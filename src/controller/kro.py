from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.db import get_session

from src.repository import kro

router = APIRouter(prefix="/kro")


@router.get("/", response_model=List[schemas.KroReadSchema])
async def get_kro(session: AsyncSession = Depends(get_session)):
    return await kro.get_kro(session)
