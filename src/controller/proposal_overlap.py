from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

from src.repository import proposal_overlap
from utils.file import decoding_file


router = APIRouter(prefix="/proposal-overlap")


@router.get("/{id}")
async def get_proposal_overlap(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        ps = await proposal_overlap.get_proposal_overlap_by_id(session, id)
        if not ps:
            raise FileNotFoundError("Proposal overlap file not found")
        if not ps.encoding_base_64:
            raise FileNotFoundError("Proposal doesn't have RAB file")
        file_io = decoding_file(ps.encoding_base_64)

        return StreamingResponse(
            file_io,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={ps.rincian_output}.pdf",
            },
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise e
