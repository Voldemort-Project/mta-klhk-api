from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models


async def get_proposal_job_by_id(
    session: AsyncSession,
    id: int,
) -> Optional[models.ProposalJob]:
    qProposalJob = select(models.ProposalJob).where(models.ProposalJob.id == id)
    rProposalJob = await session.execute(qProposalJob)
    return rProposalJob.scalars().first()


async def update_status_retry_proposal_job(
    session: AsyncSession,
    id: int,
    status: str,
) -> Optional[models.ProposalJob]:
    pj = await get_proposal_job_by_id(session, id)
    if pj:
        pj.status = status
        pj.total_failed_file = 0
        pj.total_uploaded_file = 0
        pj.is_error = False
        pj.error_message = None
        session.add(pj)
        await session.commit()
        await session.refresh(pj)
        return pj
    return None
