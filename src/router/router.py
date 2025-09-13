from fastapi import APIRouter, Depends

from src.middleware.auth_middlware import with_x_api_key
from src.controller.jenis_belanja import router as jenis_belanja_router
from src.controller.proposal import router as proposal_router
from src.controller.job import router as job_router
from src.controller.kro import router as kro_router
from src.controller.proposal_overlap import router as proposal_overlap_router


apirouter = APIRouter()


@apirouter.get("/ping")
def ping():
    return {"message": "pong"}


apirouter.include_router(jenis_belanja_router, dependencies=[Depends(with_x_api_key)])
apirouter.include_router(proposal_router, dependencies=[Depends(with_x_api_key)])
apirouter.include_router(job_router, dependencies=[Depends(with_x_api_key)])
apirouter.include_router(kro_router, dependencies=[Depends(with_x_api_key)])
apirouter.include_router(
    proposal_overlap_router,
    dependencies=[Depends(with_x_api_key)],
)
