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
    sp_file: UploadFile = File(...),
    doc_supports: Optional[List[UploadFile]] = File([]),
    session: AsyncSession = Depends(get_session),
):
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


@router.get("/", response_model=List[schemas.ProposalListReadSchema])
async def get_list_proposal(session: AsyncSession = Depends(get_session)):
    proposals = await proposal.get_list_proposal(session)
    return proposals


@router.get("/{id}/verification")
async def get_detail_proposal_verification(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await proposal.get_proposal_verification(session, id)
    return {"message": "Success", "data": result.proposal_verification}


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
    result = await proposal.get_proposal_document(session, id, type)
    return {"message": "Success", "data": result.summary if result else None}


@router.get(
    "/{id}/map-priority",
    response_model=List[schemas.ProposalMapPriorityReadSchema],
)
async def get_detail_proposal_map_priority(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await proposal.get_proposal_map_priority(session, id)
    return result
