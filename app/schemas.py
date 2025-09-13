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
    kro_id: int
    jenis_belanja_id: int
    sub_jenis_belanja_id: int

    class Config:
        from_attributes = True


class ProposalUpdateSchema(BaseModel):
    note: Optional[str] = None
    status: Optional[str] = None

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
    sp_file: UploadFile
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


class ProposalListReadSchema(BaseModel):
    id: int
    user_id: str
    jenis_belanja_id: int
    jenis_belanja: str
    sub_jenis_belanja_id: int
    sub_jenis_belanja: str
    kro_id: Optional[int]
    kro_label: Optional[str]
    satuan_kerja: Optional[str]
    anggaran: Optional[float]
    status: str
    rincian_output: Optional[str]
    created_at: datetime.datetime
    runtime_id: Optional[int]

    class Config:
        from_attributes = True


class ProposalMapPriorityReadSchema(BaseModel):
    id: int
    label: str
    score: int
    reason: Optional[str]

    class Config:
        from_attributes = True


class ProposalScoreOverlapReadSchema(BaseModel):
    id: int
    work_unit: Optional[str]
    total_budget: Optional[str]
    score: Optional[int]
    reason: Optional[str]
    rincian_output: Optional[str]

    class Config:
        from_attributes = True


class KroReadSchema(BaseModel):
    id: int
    description: Optional[str]

    class Config:
        from_attributes = True


class ProposalDocumentRetrySchema(BaseModel):
    proposal_id: int
    runtime_id: int

    class Config:
        from_attributes = True
