from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app import models
from typing import List


async def get_kro(session: AsyncSession) -> List[models.Kro] | None:
    q = select(models.Kro)
    result = await session.execute(q)
    return result.scalars().all()
