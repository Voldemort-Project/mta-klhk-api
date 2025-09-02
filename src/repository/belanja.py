from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app import models
from typing import List


async def get_jenis_belanja(session: AsyncSession) -> List[models.JenisBelanja] | None:
    q = select(models.JenisBelanja)
    result = await session.execute(q)
    return result.scalars().all()
