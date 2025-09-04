# from sqlalchemy import select
import asyncio
import base64
import datetime
import json
from re import A
import httpx

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import Any, AsyncGenerator, List, Tuple
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas
from app.config import settings
from src.constant.globals import USER_ID
from utils.clear import clear_markdown
from utils.converter import format_rupiah, string_to_float


async def create_proposal(
    session: AsyncSession,
    proposal: schemas.ProposalCreateSchema,
) -> models.Proposal:
    new_proposal = models.Proposal(
        user_id=USER_ID,
        jenis_belanja_id=proposal.jenis_belanja_id,
        sub_jenis_belanja_id=proposal.sub_jenis_belanja_id,
    )
    session.add(new_proposal)
    await session.commit()
    return new_proposal


async def upload_document_proposal(
    session: AsyncSession,
    dto: schemas.ProposalDocumentUploadSchema,
):
    doc_support_length = len(dto.doc_supports) if dto.doc_supports else 0
    total_file = 2 + doc_support_length
    bulk_proposal_document: List[models.ProposalDocument] = []
    kak_file_name, kak_file_base64 = encoding_base_64(dto.kak_file)
    rab_file_name, rab_file_base64 = encoding_base_64(dto.rab_file)
    sp_file_name, sp_file_base64 = encoding_base_64(dto.sp_file)
    proposal_job = models.ProposalJob(
        proposal_id=dto.proposal_id,
        total_file=total_file,
        status="queue",
    )
    session.add(proposal_job)
    await session.flush()
    bulk_proposal_document.extend(
        [
            models.ProposalDocument(
                proposal_id=dto.proposal_id,
                file_name=kak_file_name,
                encoding_base_64=kak_file_base64,
                type="kak",
                runtime_id=proposal_job.id,
            ),
            models.ProposalDocument(
                proposal_id=dto.proposal_id,
                file_name=rab_file_name,
                encoding_base_64=rab_file_base64,
                type="rab",
                runtime_id=proposal_job.id,
            ),
            models.ProposalDocument(
                proposal_id=dto.proposal_id,
                file_name=sp_file_name,
                encoding_base_64=sp_file_base64,
                type="sp",
                runtime_id=proposal_job.id,
            ),
        ]
    )
    if dto.doc_supports:
        for doc_support in dto.doc_supports:
            doc_support_name, doc_support_base64 = encoding_base_64(doc_support)
            bulk_proposal_document.append(
                models.ProposalDocument(
                    proposal_id=dto.proposal_id,
                    file_name=doc_support_name,
                    encoding_base_64=doc_support_base64,
                    type="doc_support",
                    runtime_id=proposal_job.id,
                )
            )
    session.add_all(bulk_proposal_document)
    await session.commit()
    await session.refresh(proposal_job)
    return proposal_job


async def background_process_job_agent(
    session: AsyncSession,
    job_id: int,
    proposal_id: int,
):
    print(f"Background Process Job Agent {job_id} {proposal_id}")
    qProposalDocument = select(models.ProposalDocument).where(
        models.ProposalDocument.runtime_id == job_id,
        models.ProposalDocument.proposal_id == proposal_id,
    )
    rProposalDocument = await session.execute(qProposalDocument)
    propDocs = rProposalDocument.scalars().all()
    qProposalJob = select(models.ProposalJob).where(models.ProposalJob.id == job_id)
    rProposalJob = await session.execute(qProposalJob)
    propJob = rProposalJob.scalars().first()

    qProposal = (
        select(models.Proposal)
        .options(
            joinedload(models.Proposal.jenis_belanja),
            joinedload(models.Proposal.sub_jenis_belanja),
        )
        .where(models.Proposal.id == proposal_id)
    )
    rProposal = await session.execute(qProposal)
    proposal = rProposal.scalars().first()

    propJob.status = "running"
    session.add(propJob)
    await session.commit()
    await session.refresh(propJob)

    is_error_upload = False

    # Generate Summary
    urlSummary = f"{settings.agent_url}/api/v1/parse-single-base64"
    # Generate Assess Document | Allignment Assessor
    urlAssessDocument = f"{settings.agent_url}/api/v1/assess-documents"
    # Text Extractor -> Buat lengkapin proposal value
    urlExtractDocument = f"{settings.agent_url}/api/v1/extract-from-base64"
    # Overlap Comparator
    urlOverlapComparator = f"{settings.agent_url}/api/v1/overlap-comparator-vector"
    # Summarizer
    urlSummarizer = f"{settings.agent_url}/api/v1/summarizer"

    # Hasil Generator Recommendation
    urlGeneratorRecommendation = f"{settings.agent_url}/api/v1/recommendation-generator"

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": settings.agent_api_key,
    }

    async with httpx.AsyncClient(timeout=1800) as client:
        for doc in propDocs:
            bodySummary = create_body_proposal_doc_summary(doc)
            print(f"Extract Summary {doc.file_name}")
            try:
                res_summary = await client.post(
                    urlSummary,
                    json=bodySummary,
                    headers=headers,
                )

                if res_summary.status_code != 200:
                    print(f"Error Extract Summary {doc.file_name}")
                    propJob.total_failed_file += 1
                    continue

                res_summary = res_summary.json()
                doc.summary = res_summary["data"]

                propJob.total_uploaded_file += 1
            except Exception as e:
                print(f"Error Hit API: {e}")
                propJob.total_failed_file += 1

        is_error_upload = propJob.total_failed_file > 0

        if await check_or_throw_error(
            session, propJob, is_error_upload, "Error Upload Document"
        ):
            return

        # Get Proposal Verification
        body_verification = create_body_proposal_verification(propDocs)
        print(f"Extract Verification")
        res_verification = await client.post(
            urlAssessDocument,
            json=body_verification,
            headers=headers,
        )
        if res_verification.status_code != 200:
            print(f"Error Extract Verification")
            propJob.status = "failed"
            is_error_upload = True
        else:
            res_verification_json = res_verification.json()
            proposal.proposal_verification = clear_markdown(
                res_verification_json["result"]["data"]
            )

        if await check_or_throw_error(
            session, propJob, is_error_upload, "Error Extract Verification Document"
        ):
            return

        kak_base64 = [item for item in propDocs if item.type == "kak"][
            0
        ].encoding_base_64
        kak_summary = [item for item in propDocs if item.type == "kak"][0].summary
        jenis_belanja = proposal.jenis_belanja.label
        sub_jenis_belanja = proposal.sub_jenis_belanja.label

        # Get Proposal Map Priority
        proposalMapPriorities: List[models.ProposalMapPriority] = []
        for file in ["rkp-lhk.md", "rkp-nasional.md", "rpjmn-lhk.md"]:
            label = file.split(".")[0].upper()
            print(f"Extract Map Priority {label}")
            body_map_priority = create_body_proposal_allignment(
                file,
                kak_base64,
                jenis_belanja,
                sub_jenis_belanja,
            )
            res_map_priority = await client.post(
                urlAssessDocument,
                json=body_map_priority,
                headers=headers,
            )
            if res_map_priority.status_code != 200:
                print(f"Error Extract Map Priority {label}")
                is_error_upload = True
                continue
            else:
                res_map_priority_json = res_map_priority.json()
                res_map_priority_data = res_map_priority_json["result"]

                p = models.ProposalMapPriority(
                    proposal_id=proposal_id,
                    label=label,
                    score=res_map_priority_data["skor"],
                    reason=res_map_priority_data["alasan"],
                )
                proposalMapPriorities.append(p)

        if await check_or_throw_error(
            session, propJob, is_error_upload, "Error Extract Map Priority"
        ):
            return

        # Create Extractor Proposal
        body_extractor_proposal = create_body_proposal_extractor(kak_base64)
        res_extractor_proposal = await client.post(
            urlExtractDocument,
            json=body_extractor_proposal,
            headers=headers,
        )
        print(f"Extract Extractor Proposal")
        if res_extractor_proposal.status_code != 200:
            print(f"Error Extract Extractor Proposal")
            is_error_upload = True
        else:
            res_extractor_proposal_json = res_extractor_proposal.json()
            output_extactor = res_extractor_proposal_json["data"]
            proposal_allignment_response = str([output_extactor])

            for output in output_extactor:
                if output["key"] == "Rincian Output":
                    proposal.rincian_output = output["value"]
                elif output["key"] == "Direktorat":
                    proposal.satuan_kerja = output["value"]
                elif output["key"] == "Total Biaya":
                    proposal.anggaran = string_to_float(output["value"])

        if await check_or_throw_error(
            session, propJob, is_error_upload, "Error Extract Extractor Proposal"
        ):
            return

        # Create Proposal Score Overlap
        proposalScoreOverlaps: List[models.ProposalScoreOverlap] = []
        body_score_overlap = create_body_overlap_vector(kak_summary, kak_base64)
        print(f"Extract Score Overlap")
        res_score_overlap = await client.post(
            urlOverlapComparator,
            json=body_score_overlap,
            headers=headers,
        )
        if res_score_overlap.status_code != 200:
            print(f"Error Extract Score Overlap")
            is_error_upload = True
        else:
            res_score_overlap_json = res_score_overlap.json()
            res_score_overlap_data = res_score_overlap_json["result"]
            for each in res_score_overlap_data:
                p = models.ProposalScoreOverlap(
                    proposal_id=proposal_id,
                    work_unit=each["direktorat"],
                    score=each["skor"],
                    total_budget=string_to_float(each["total_biaya"]),
                    reason=each["alasan"],
                    rincian_output=each["rincian_output"],
                )
                proposalScoreOverlaps.append(p)

        if await check_or_throw_error(
            session, propJob, is_error_upload, "Error Extract Score Overlap"
        ):
            return

        # Create Proposal Summary
        body_proposal_summary = create_body_proposal_summary(
            proposal_verification_response=proposal.proposal_verification,
            proposal_allignment_response=proposal_allignment_response,
            overlap_vector_response=str(res_score_overlap_data),
        )
        print(f"Extract Proposal Summary")
        res_proposal_summary = await client.post(
            urlSummarizer,
            json=body_proposal_summary,
            headers=headers,
        )
        if res_proposal_summary.status_code != 200:
            print(f"Error Extract Proposal Summary")
            is_error_upload = True
        else:
            res_proposal_summary_json = res_proposal_summary.json()
            proposal.summary = clear_markdown(res_proposal_summary_json["data"])

        if await check_or_throw_error(
            session, propJob, is_error_upload, "Error Extract Proposal Summary"
        ):
            return

        # Create Proposal Evaluation Letter
        body_evaluation_letter = create_body_proposal_evaluation_letter(proposal)
        print(f"Extract Proposal Evaluation Letter")
        res_evaluation_letter = await client.post(
            urlGeneratorRecommendation,
            json=body_evaluation_letter,
            headers=headers,
        )
        if res_evaluation_letter.status_code != 200:
            print(f"Error Extract Proposal Evaluation Letter")
            is_error_upload = True
        else:
            res_evaluation_letter_json = res_evaluation_letter.json()
            proposal.evaluasi_letter = clear_markdown(
                res_evaluation_letter_json["data"]
            )

        if await check_or_throw_error(
            session,
            propJob,
            is_error_upload,
            "Error Extract Proposal Evaluation Letter",
        ):
            return

    propJob.status = "completed"
    propJob.completed_at = datetime.datetime.now()

    print(f"Proposal Job {propJob.status}")

    session.add_all(proposalMapPriorities)
    session.add_all(proposalScoreOverlaps)
    session.add_all(propDocs)
    session.add(proposal)
    session.add(propJob)

    await session.commit()
    await session.close()


# ===============================
# Helper Function
# ===============================
def encoding_base_64(file: UploadFile) -> Tuple[str, str]:
    return file.filename, base64.b64encode(file.file.read()).decode("utf-8")


def get_llm_config(temperature: float = 0.7) -> dict:
    return {
        "model_provider": "google",
        "model_name": "gemini-2.0-flash",
        "temperature": temperature,
    }


def create_body_proposal_doc_summary(doc: models.ProposalDocument) -> dict:
    return {
        "base64_data": doc.encoding_base_64,
        "filename": doc.file_name,
        "raw_input": "",
        "category": str(doc.type).upper() if doc.type != "doc_support" else "",
        "llm_config": get_llm_config(temperature=1.0),
    }


def create_body_proposal_verification(docs: List[models.ProposalDocument]) -> dict:
    return {
        "reference_document_name": "sop-clearance.md",
        "base64_data": [doc.encoding_base_64 for doc in docs],
        "filenames": [
            str(doc.type).upper() if doc.type != "doc_support" else "" for doc in docs
        ],
        "llm_config": get_llm_config(),
    }


# Pemetaan Prioritas
def create_body_proposal_allignment(
    reference_doc: str,
    kak_base64: str,
    jenis_belanja: str,
    kode_belanja: str,
) -> dict:
    return {
        "reference_document_name": reference_doc,
        "base64_data": [kak_base64],
        "filenames": ["KAK"],
        "llm_config": get_llm_config(),
        "free_text": f"Dokumen yang masuk sudah teridentifikasi sebagai Kategori {jenis_belanja}, Kode KRO: {kode_belanja}",
    }


def create_body_proposal_extractor(kak_base64: str) -> dict:
    return {
        "base64_data": kak_base64,
        "filename": "KAK",
        "raw_input": "",
        "llm_config": get_llm_config(),
    }


def create_body_overlap_vector(summary_kak: str, base_64_kak: str) -> dict:
    return {
        "raw_input": summary_kak,
        "base64_data": base_64_kak,
        "llm_config": get_llm_config(),
    }


def create_body_proposal_summary(
    proposal_verification_response: str,
    proposal_allignment_response: str,
    overlap_vector_response: str,
) -> dict:
    return {
        "markdown_summary": proposal_verification_response,
        "assessor_summary": proposal_allignment_response,
        "overlap_summary": overlap_vector_response,
        "llm_config": get_llm_config(),
    }


# Recomendation
def create_body_proposal_evaluation_letter(doc: models.Proposal) -> dict:
    return {
        "direktorat": doc.satuan_kerja,
        "rincian_output": doc.rincian_output,
        "total_biaya": str(doc.anggaran),
        "summarizer_text": doc.summary,
        "user_remarks": doc.note if doc.note else "",
        "llm_config": get_llm_config(),
    }


async def check_or_throw_error(
    session: AsyncSession,
    propJob: models.ProposalJob,
    is_error: bool = False,
    err: Any = None,
) -> bool:
    if is_error:
        print(f"An error is occurred: {err if err else 'Unknown error'}")
        propJob.status = "completed"
        propJob.completed_at = datetime.datetime.now()
        propJob.is_error = True
        propJob.error_message = err if err else "Unknown error"
        session.add(propJob)
        await session.commit()
        await session.close()
        return True
    return False


async def get_proposal_job(session: AsyncSession, job_id: int) -> models.ProposalJob:
    qProposalJob = select(models.ProposalJob).where(models.ProposalJob.id == job_id)
    rProposalJob = await session.execute(qProposalJob)
    return rProposalJob.scalars().first()


async def get_proposal_job_stream(
    session: AsyncSession,
    job_id: int,
) -> AsyncGenerator[str, None]:
    propJob = await get_proposal_job(session, job_id)
    while propJob.status != "completed":
        propJob = await get_proposal_job(session, job_id)
        data = {
            "id": propJob.id,
            "status": propJob.status,
            "completed_at": propJob.completed_at,
            "total_file": propJob.total_file,
            "total_uploaded_file": propJob.total_uploaded_file,
            "total_failed_file": propJob.total_failed_file,
            "error_message": propJob.error_message,
            "is_error": propJob.is_error,
        }
        yield f"data: {json.dumps(data)}\n\n"

        await session.refresh(propJob)

        if propJob.status == "completed":
            data = {
                "id": propJob.id,
                "status": propJob.status,
                "completed_at": propJob.completed_at.strftime("%Y-%m-%d %H:%M:%S"),
                "total_file": propJob.total_file,
                "total_uploaded_file": propJob.total_uploaded_file,
                "total_failed_file": propJob.total_failed_file,
                "error_message": propJob.error_message,
                "is_error": propJob.is_error,
            }
            yield f"data: {json.dumps(data)}\n\n"
            break

        await asyncio.sleep(1)


async def get_list_proposal(session: AsyncSession) -> List[models.Proposal]:
    qProposal = (
        select(
            models.Proposal.id,
            models.Proposal.user_id,
            models.Proposal.jenis_belanja_id,
            models.JenisBelanja.label.label("jenis_belanja"),
            models.Proposal.sub_jenis_belanja_id,
            models.SubJenisBelanja.label.label("sub_jenis_belanja"),
            models.Proposal.satuan_kerja,
            models.Proposal.anggaran,
            models.Proposal.status,
            models.Proposal.rincian_output,
        )
        .join(
            models.JenisBelanja,
            models.JenisBelanja.id == models.Proposal.jenis_belanja_id,
        )
        .join(
            models.SubJenisBelanja,
            models.SubJenisBelanja.id == models.Proposal.sub_jenis_belanja_id,
        )
        .where(models.Proposal.user_id == USER_ID)
    )
    rProposal = await session.execute(qProposal)
    return rProposal.mappings().all()


async def get_proposal_by_id(
    session: AsyncSession,
    proposal_id: int,
) -> models.Proposal:
    qProposal = select(models.Proposal).where(models.Proposal.id == proposal_id)
    rProposal = await session.execute(qProposal)
    return rProposal.scalars().first()


async def get_proposal_document(
    session: AsyncSession,
    proposal_id: int,
    type: str,
) -> models.ProposalDocument:
    qProposalDocument = select(models.ProposalDocument).where(
        models.ProposalDocument.proposal_id == proposal_id,
        models.ProposalDocument.type == type,
    )
    rProposalDocument = await session.execute(qProposalDocument)
    return rProposalDocument.scalars().first()


async def get_proposal_map_priority(
    session: AsyncSession,
    proposal_id: int,
) -> List[models.ProposalMapPriority]:
    qProposalMapPriority = select(models.ProposalMapPriority).where(
        models.ProposalMapPriority.proposal_id == proposal_id,
    )
    rProposalMapPriority = await session.execute(qProposalMapPriority)
    return rProposalMapPriority.scalars().all()


async def get_proposal_score_overlap(
    session: AsyncSession,
    proposal_id: int,
) -> List[models.ProposalScoreOverlap]:
    qProposalScoreOverlap = select(models.ProposalScoreOverlap).where(
        models.ProposalScoreOverlap.proposal_id == proposal_id,
    )
    rProposalScoreOverlap = await session.execute(qProposalScoreOverlap)
    docs = rProposalScoreOverlap.scalars().all()
    for doc in docs:
        doc.total_budget = format_rupiah(doc.total_budget)
    return docs
