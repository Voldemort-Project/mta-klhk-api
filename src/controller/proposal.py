from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas
from app.db import get_session
from src.repository import proposal


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


@router.post("/", response_model=schemas.ProposalCreateSchema)
async def create_proposal(
    input: schemas.ProposalCreateSchema,
    session: AsyncSession = Depends(get_session),
):
    new_proposal = await proposal.create_proposal(session, input)
    return new_proposal


@router.post("/document")
async def upload_document_proposal(
    background_tasks: BackgroundTasks,
    proposal_id: int = Form(...),
    kak_file: UploadFile = File(...),
    rab_file: UploadFile = File(...),
    doc_supports: Optional[List[UploadFile]] = File([]),
    session: AsyncSession = Depends(get_session),
):
    dto = schemas.ProposalDocumentUploadSchema(
        proposal_id=proposal_id,
        kak_file=kak_file,
        rab_file=rab_file,
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


@router.get("/")
def get_list_budget():
    return {"message": "budget fetched"}


@router.get("/{id}")
def get_detail_budget():
    return {"message": "budget fetched"}
