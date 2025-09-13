from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models


async def get_proposal_overlap_by_id(
    session: AsyncSession,
    id: int,
) -> models.ProposalScoreOverlap:
    qProposalScoreOverlap = select(models.ProposalScoreOverlap).where(
        models.ProposalScoreOverlap.id == id
    )
    rProposalScoreOverlap = await session.execute(qProposalScoreOverlap)
    return rProposalScoreOverlap.scalars().first()
