from fastapi import APIRouter
from src.controller.jenis_belanja import router as jenis_belanja_router
from src.controller.proposal import router as proposal_router


apirouter = APIRouter()


@apirouter.get("/ping")
def ping():
    return {"message": "pong"}


apirouter.include_router(jenis_belanja_router)
apirouter.include_router(proposal_router)
