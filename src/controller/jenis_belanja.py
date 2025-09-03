from typing import List
from fastapi import APIRouter, Depends
from app import schemas
from sqlalchemy.ext.asyncio import AsyncSession
from src.repository import belanja

from app.db import get_session


router = APIRouter(prefix="/jenis-belanja")


@router.get("/type", response_model=List[schemas.JenisBelanjaReadSchema])
async def get_shopping_type(session: AsyncSession = Depends(get_session)):
    results = await belanja.get_jenis_belanja(session)
    return results


@router.get(
    "/{id}/sub-type",
    response_model=List[schemas.SubJenisBelanjaReadOptionSchema],
)
async def get_shopping_sub_type(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    results = await belanja.get_sub_jenis_belanja(session, id)
    return results
