from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from src.repository import proposal


router = APIRouter(prefix="/job")


@router.get("/{id}")
async def get_job(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    return StreamingResponse(
        proposal.get_proposal_job_stream(session, id),
        media_type="text/event-stream",
    )
