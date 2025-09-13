from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models


async def get_proposal_document_by_proposal_id_and_type(
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
