from fastapi import HTTPException, Header

from app.config import settings


async def with_x_api_key(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=403, detail="Forbidden resource")

    if x_api_key != settings.x_api_key:
        raise HTTPException(
            status_code=401, detail="You dont have access to this resource"
        )
