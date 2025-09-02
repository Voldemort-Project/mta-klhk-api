import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.db import Base


class JenisBelanja(Base):
    __tablename__ = "jenis_belanja"

    id = Column(Integer, primary_key=True)
    label = Column(String)
    description = Column(String, nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    sub_jenis_belanja = relationship(
        "SubJenisBelanja", back_populates="jenis_belanja", cascade="all, delete-orphan"
    )
    proposal = relationship("Proposal", back_populates="jenis_belanja")


class SubJenisBelanja(Base):
    __tablename__ = "sub_jenis_belanja"

    id = Column(Integer, primary_key=True)
    shoping_id = Column(
        Integer, ForeignKey("jenis_belanja.id", ondelete="CASCADE"), nullable=False
    )
    label = Column(String)
    description = Column(String, nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    jenis_belanja = relationship("JenisBelanja", back_populates="sub_jenis_belanja")
    proposal = relationship("Proposal", back_populates="sub_jenis_belanja")


class Proposal(Base):
    __tablename__ = "proposal"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now)
    user_id = Column(String, nullable=False)
    jenis_belanja_id = Column(
        Integer, ForeignKey("jenis_belanja.id", ondelete="CASCADE"), nullable=False
    )
    sub_jenis_belanja_id = Column(
        Integer, ForeignKey("sub_jenis_belanja.id", ondelete="CASCADE"), nullable=False
    )
    satuan_kerja = Column(String, nullable=True)
    anggaran = Column(Numeric, nullable=True, default=0)
    status = Column(String, nullable=True, default="waiting")
    jenis_belanja = relationship("JenisBelanja", back_populates="proposal")
    sub_jenis_belanja = relationship("SubJenisBelanja", back_populates="proposal")
    proposal_document = relationship("ProposalDocument", back_populates="proposal")
    proposal_job = relationship("ProposalJob", back_populates="proposal")


class ProposalDocument(Base):
    __tablename__ = "proposal_document"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now)
    type = Column(String, nullable=False)
    proposal_id = Column(
        Integer,
        ForeignKey("proposal.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name = Column(String, nullable=False)
    encoding_base_64 = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    assess_document = Column(Text, nullable=True)
    runtime_id = Column(
        Integer,
        ForeignKey("proposal_job.id", ondelete="CASCADE"),
        nullable=True,
    )
    proposal = relationship("Proposal", back_populates="proposal_document")
    runtime = relationship("ProposalJob", back_populates="proposal_document")


class ProposalJob(Base):
    __tablename__ = "proposal_job"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now)
    proposal_id = Column(
        Integer,
        ForeignKey("proposal.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String, nullable=False, default="waiting")
    total_file = Column(Integer, nullable=False, default=0)
    total_failed_file = Column(Integer, nullable=False, default=0)
    total_uploaded_file = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime, nullable=True)
    proposal = relationship("Proposal", back_populates="proposal_job")
    proposal_document = relationship("ProposalDocument", back_populates="runtime")
