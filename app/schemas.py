import datetime
from typing import List, Optional
from fastapi import UploadFile
from pydantic import BaseModel


class JenisBelanjaReadSchema(BaseModel):
    id: int
    label: str

    class Config:
        from_attributes = True


class SubJenisBelanjaReadOptionSchema(BaseModel):
    id: int
    label: str

    class Config:
        from_attributes = True


class ProposalCreateSchema(BaseModel):
    user_id: str
    jenis_belanja_id: int
    sub_jenis_belanja_id: int

    class Config:
        from_attributes = True


class ProposalDocumentCreateSchema(BaseModel):
    file_name: str
    encoding_base_64: str
    summary: Optional[str]
    assess_document: Optional[str]

    class Config:
        from_attributes = True


class ProposalDocumentUploadSchema(BaseModel):
    proposal_id: int
    kak_file: UploadFile
    rab_file: UploadFile
    doc_supports: Optional[List[UploadFile]]


class ProposalJobCreateSchema(BaseModel):
    proposal_id: int
    status: Optional[str]
    completed_at: Optional[datetime.datetime]
    total_file: Optional[int]

    class Config:
        from_attributes = True


class ProposalScoreOverlapCreateSchema(BaseModel):
    proposal_id: int
    work_unit: Optional[str]
    total_budget: Optional[float]
    score: Optional[int]
    reason: Optional[str]

    class Config:
        from_attributes = True
