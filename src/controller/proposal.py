from typing import List, Optional
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas
from app.db import get_session
from src.repository import proposal, proposal_job, proposal_document
from utils import file as utils_file
from fastapi.responses import StreamingResponse


router = APIRouter(prefix="/proposal")


# ===============================
# Background process Job
# ===============================
async def background_process_job(
    session: AsyncSession,
    job_id: int,
    proposal_id: int,
):
    await proposal.background_process_job_agent(session, job_id, proposal_id)


@router.post("/")
async def create_proposal(
    input: schemas.ProposalCreateSchema,
    session: AsyncSession = Depends(get_session),
):
    try:
        new_proposal = await proposal.create_proposal(session, input)
        return {
            "message": "Success create proposal",
            "data": {"proposal_id": new_proposal.id},
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/document")
async def upload_document_proposal(
    background_tasks: BackgroundTasks,
    proposal_id: int = Form(...),
    kak_file: UploadFile = File(...),
    rab_file: UploadFile = File(...),
    sp_file: UploadFile = File(...),
    doc_supports: Optional[List[UploadFile]] = File([]),
    session: AsyncSession = Depends(get_session),
):
    is_error = False
    try:
        dto = schemas.ProposalDocumentUploadSchema(
            proposal_id=proposal_id,
            kak_file=kak_file,
            rab_file=rab_file,
            sp_file=sp_file,
            doc_supports=doc_supports,
        )

        job = await proposal.upload_document_proposal(session, dto)
        background_tasks.add_task(
            background_process_job,
            session,
            job.id,
            proposal_id,
        )

        return {
            "message": "document uploaded",
            "data": job.id,
        }
    except Exception as exc:
        is_error = True
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if not is_error:
            await proposal.update_proposal(
                session,
                proposal_id,
                schemas.ProposalUpdateSchema(runtime_id=job.id),
            )


@router.get("/", response_model=List[schemas.ProposalListReadSchema])
async def get_list_proposal(session: AsyncSession = Depends(get_session)):
    try:
        proposals = await proposal.get_list_proposal(session)
        return proposals
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}/verification")
async def get_detail_proposal_verification(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await proposal.get_proposal_by_id(session, id)
        return {
            "message": "Success",
            "data": result.proposal_verification if result else None,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}/document")
async def get_detail_proposal_document(
    id: int,
    type: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    if type not in ["kak", "rab", "sp"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid type. Should be kak, rab, or sp",
        )
    try:
        result = await proposal.get_proposal_document(session, id, type)
        return {"message": "Success", "data": result.summary if result else None}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{id}/map-priority",
    response_model=List[schemas.ProposalMapPriorityReadSchema],
)
async def get_detail_proposal_map_priority(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await proposal.get_proposal_map_priority(session, id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{id}/score-overlap",
    response_model=List[schemas.ProposalScoreOverlapReadSchema],
)
async def get_detail_proposal_score_overlap(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await proposal.get_proposal_score_overlap(session, id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}/summary")
async def get_detail_proposal_summary(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await proposal.get_proposal_by_id(session, id)
        return {
            "message": "Success",
            "data": {
                "summary": result.summary if result else None,
                "note": result.note if result else None,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}/evaluation-letter")
async def get_detail_evaluation_letter(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await proposal.get_proposal_by_id(session, id)
        return {
            "message": "Success",
            "data": result.evaluasi_letter if result else None,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{id}/notes")
async def update_proposal_notes(
    id: int,
    input: schemas.ProposalUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    try:
        await proposal.update_proposal(session, id, input)
        return {"message": "Success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{id}/status")
async def update_proposal_status(
    id: int,
    input: schemas.ProposalUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    try:
        await proposal.update_proposal(
            session,
            id,
            schemas.ProposalUpdateSchema(status=input.status),
        )
        return {
            "message": "Success update status proposal",
            "data": {"id": id, "status": input.status},
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/document/retry")
async def retry_upload_document_proposal(
    background_tasks: BackgroundTasks,
    input: schemas.ProposalDocumentRetrySchema,
    session: AsyncSession = Depends(get_session),
):
    try:
        pj = await proposal_job.get_proposal_job_by_id(session, input.runtime_id)
        if not pj:
            raise HTTPException(status_code=404, detail="Proposal job not found")
        await proposal_job.update_status_retry_proposal_job(
            session,
            input.runtime_id,
            "queue",
        )
        await proposal.update_proposal(
            session,
            input.proposal_id,
            schemas.ProposalUpdateSchema(status="retry"),
        )
        background_tasks.add_task(
            background_process_job,
            session,
            input.runtime_id,
            input.proposal_id,
        )
        return {
            "message": "Retry upload document proposal in progress",
            "data": input.runtime_id,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}/document/download")
async def download_document_proposal(
    id: int,
    type: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    try:
        if type not in ["rab", "overlap"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid type. Should be rab",
            )
        doc = await proposal_document.get_proposal_document_by_proposal_id_and_type(
            session,
            id,
            type,
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        file_io = utils_file.decoding_file(doc.encoding_base_64)

        return StreamingResponse(
            file_io,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={doc.file_name}",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}", response_model=schemas.ProposalListReadSchema)
async def get_proposal_by_id(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        pr = await proposal.get_proposal_detail_by_id(session, id)
        return pr
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
