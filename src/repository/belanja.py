from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app import models
from typing import List


async def get_jenis_belanja(session: AsyncSession) -> List[models.JenisBelanja] | None:
    q = select(models.JenisBelanja)
    result = await session.execute(q)
    return result.scalars().all()


async def get_sub_jenis_belanja(
    session: AsyncSession,
    id: int,
) -> List[models.SubJenisBelanja] | None:
    q = select(models.SubJenisBelanja).where(
        models.SubJenisBelanja.jenis_belanja_id == id
    )
    result = await session.execute(q)
    return result.scalars().all()
