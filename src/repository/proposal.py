# from sqlalchemy import select
import base64
import datetime
import httpx

from sqlalchemy import select
from typing import List, Tuple
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas
from app.config import settings


async def create_proposal(
    session: AsyncSession, proposal: schemas.ProposalCreateSchema
) -> models.Proposal:
    new_proposal = models.Proposal(
        user_id=proposal.user_id,
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

    propJob.status = "running"
    session.add(propJob)
    await session.commit()
    await session.refresh(propJob)
    async with httpx.AsyncClient(timeout=900) as client:
        for doc in propDocs:
            bodySummary = {
                "base64_data": doc.encoding_base_64,
                "filename": doc.file_name,
                "raw_input": "",
                "category": str(doc.type).upper() if doc.type != "doc_support" else "",
                "llm_config": {
                    "model_provider": "google",
                    "model_name": "gemini-2.0-flash",
                    "temperature": 1.0,
                },
            }
            urlSummary = f"{settings.agent_url}/api/v1/parse-single-base64"
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": settings.agent_api_key,
            }
            try:
                res_summary = await client.post(
                    urlSummary,
                    json=bodySummary,
                    headers=headers,
                )

                if res_summary.status_code != 200:
                    propJob.total_failed_file += 1
                    session.add(propJob)
                    await session.commit()
                    await session.refresh(propJob)
                    continue

                res_summary = res_summary.json()
                doc.summary = res_summary["data"]
                session.add(doc)
                await session.commit()
                await session.refresh(doc)

                propJob.total_uploaded_file += 1
                session.add(propJob)
                await session.commit()
                await session.refresh(propJob)
            except Exception as e:
                print(f"Error Hit API: {e}")
                propJob.total_failed_file += 1
                session.add(propJob)
                await session.commit()
                await session.refresh(propJob)

    propJob.status = "completed"
    propJob.completed_at = datetime.datetime.now()

    session.add(propJob)
    await session.commit()
    await session.refresh(propJob)
    await session.close()


# ===============================
# Helper Function
# ===============================
def encoding_base_64(file: UploadFile) -> Tuple[str, str]:
    return file.filename, base64.b64encode(file.file.read()).decode("utf-8")
