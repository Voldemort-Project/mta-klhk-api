from typing import List, Optional
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas
from app.db import get_session
from src.repository import proposal, proposal_job, proposal_document
from utils import file as utils_file
from fastapi.responses import StreamingResponse
from src.utils.converter import md_to_pdf_xhtml2pdf


router = APIRouter(prefix="/proposal")


# ===============================
# Background process Job
# ===============================
async def background_process_job(
    session: AsyncSession,
    job_id: int,
    proposal_id: int,
):
    await proposal.background_process_job_agent(session, job_id, proposal_id)


@router.post("/")
async def create_proposal(
    input: schemas.ProposalCreateSchema,
    session: AsyncSession = Depends(get_session),
):
    try:
        new_proposal = await proposal.create_proposal(session, input)
        return {
            "message": "Success create proposal",
            "data": {"proposal_id": new_proposal.id},
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/document")
async def upload_document_proposal(
    background_tasks: BackgroundTasks,
    proposal_id: int = Form(...),
    kak_file: UploadFile = File(...),
    rab_file: UploadFile = File(...),
    sp_file: UploadFile = File(...),
    doc_supports: Optional[List[UploadFile]] = File([]),
    session: AsyncSession = Depends(get_session),
):
    is_error = False
    try:
        dto = schemas.ProposalDocumentUploadSchema(
            proposal_id=proposal_id,
            kak_file=kak_file,
            rab_file=rab_file,
            sp_file=sp_file,
            doc_supports=doc_supports,
        )

        job = await proposal.upload_document_proposal(session, dto)
        background_tasks.add_task(
            background_process_job,
            session,
            job.id,
            proposal_id,
        )

        return {
            "message": "document uploaded",
            "data": job.id,
        }
    except Exception as exc:
        is_error = True
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if not is_error:
            await proposal.update_proposal(
                session,
                proposal_id,
                schemas.ProposalUpdateSchema(runtime_id=job.id),
            )


@router.get("/", response_model=List[schemas.ProposalListReadSchema])
async def get_list_proposal(session: AsyncSession = Depends(get_session)):
    try:
        proposals = await proposal.get_list_proposal(session)
        return proposals
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}/verification")
async def get_detail_proposal_verification(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await proposal.get_proposal_by_id(session, id)
        return {
            "message": "Success",
            "data": result.proposal_verification if result else None,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}/document")
async def get_detail_proposal_document(
    id: int,
    type: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    if type not in ["kak", "rab", "sp"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid type. Should be kak, rab, or sp",
        )
    try:
        result = await proposal.get_proposal_document(session, id, type)
        return {"message": "Success", "data": result.summary if result else None}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{id}/map-priority",
    response_model=List[schemas.ProposalMapPriorityReadSchema],
)
async def get_detail_proposal_map_priority(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await proposal.get_proposal_map_priority(session, id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{id}/score-overlap",
    response_model=List[schemas.ProposalScoreOverlapReadSchema],
)
async def get_detail_proposal_score_overlap(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await proposal.get_proposal_score_overlap(session, id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}/summary")
async def get_detail_proposal_summary(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await proposal.get_proposal_by_id(session, id)
        return {
            "message": "Success",
            "data": {
                "summary": result.summary if result else None,
                "note": result.note if result else None,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}/evaluation-letter")
async def get_detail_evaluation_letter(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await proposal.get_proposal_by_id(session, id)
        return {
            "message": "Success",
            "data": result.evaluasi_letter if result else None,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{id}/notes")
async def update_proposal_notes(
    id: int,
    input: schemas.ProposalUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    try:
        await proposal.update_proposal(session, id, input)
        return {"message": "Success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{id}/status")
async def update_proposal_status(
    id: int,
    input: schemas.ProposalUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    try:
        await proposal.update_proposal(
            session,
            id,
            schemas.ProposalUpdateSchema(status=input.status),
        )
        return {
            "message": "Success update status proposal",
            "data": {"id": id, "status": input.status},
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/document/retry")
async def retry_upload_document_proposal(
    background_tasks: BackgroundTasks,
    input: schemas.ProposalDocumentRetrySchema,
    session: AsyncSession = Depends(get_session),
):
    try:
        pj = await proposal_job.get_proposal_job_by_id(session, input.runtime_id)
        if not pj:
            raise HTTPException(status_code=404, detail="Proposal job not found")
        await proposal_job.update_status_retry_proposal_job(
            session,
            input.runtime_id,
            "queue",
        )
        await proposal.update_proposal(
            session,
            input.proposal_id,
            schemas.ProposalUpdateSchema(status="retry"),
        )
        background_tasks.add_task(
            background_process_job,
            session,
            input.runtime_id,
            input.proposal_id,
        )
        return {
            "message": "Retry upload document proposal in progress",
            "data": input.runtime_id,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}/document/download")
async def download_document_proposal(
    id: int,
    type: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    try:
        if type not in ["rab", "kak"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid type. Should be rab or kak",
            )
        doc = await proposal_document.get_proposal_document_by_proposal_id_and_type(
            session,
            id,
            type,
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        file_io = utils_file.decoding_file(doc.encoding_base_64)

        return StreamingResponse(
            file_io,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={doc.file_name}",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{id}", response_model=schemas.ProposalListReadSchema)
async def get_proposal_by_id(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        pr = await proposal.get_proposal_detail_by_id(session, id)
        return pr
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/{id}/evaluation-letter/download")
async def download_detail_evaluation_letter(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await proposal.get_proposal_by_id(session, id)
        sample_md = r"""
## Berita Acara Hasil Evaluasi Proposal

Nomor: KM/2025/BA/SPBE/1

<table>
    <tr>
        <td style="width: 30%;">Judul Proposal</td>
        <td>: Data dan Peta Kondisi Sumber Daya Hutan dan Kawasan Hutan</td>
    </tr>
    <tr>
        <td style="width: 30%;">Pengusul</td>
        <td>: Direktorat Inventarisasi dan Pemantauan Sumber Daya Hutan</td>
    </tr>
    <tr>
        <td style="width: 30%;">Estimasi Biaya</td>
        <td>: Rp. 950.000.000</td>
    </tr>
    <tr>
        <td style="width: 30%;">Tanggal Pengajuan</td>
        <td>: 27 September 2025</td>
    </tr>
</table>


Evaluasi ini dilakukan untuk memastikan kesesuaian proposal dengan SOP Budget Clearance, kelengkapan dokumen, keselarasan rencana dan tugas fungsi serta menghindari potensi tumpang tindih dengan kegiatan lainnya.

Ringkasan Kajian adalah sebagai berikut:

1. Proposal yang diajukan oleh Direktorat Inventarisasi dan Pemantauan Sumber Daya Hutan dengan judul "Data dan Peta Kondisi Sumber Daya Hutan dan Kawasan Hutan" dinilai relevan dengan KRO Belanja Data (BMA/QMA).
2. Penilaian oleh *assessor* menunjukkan keselarasan yang kuat (skor 85) dengan agenda strategis Kementerian LHK, terutama dalam Tata Ruang dan Pengelolaan Wilayah, serta Pemanfaatan IPTEK dan Peningkatan SDM LHK. Proposal ini mendukung inventarisasi dan pemantauan sumber daya hutan.
3. Proposal belum menyertakan dokumen pendukung yang dipersyaratkan seperti Kerangka Acuan Kerja (KAK) yang lengkap, Dokumen Arsitektur SPBE Domain Data dan Informasi, Rujukan regulasi dalam melakukan Kegiatan Pendataan minimum Data prioritas, Surat Rekomendasi BPS (jika relevan), dan Daftar Data (Formulir isian daftar data).
4. Terdapat potensi tumpang tindih dengan program pemantauan SDH (skor 35 dan 60), khususnya dalam penggunaan data citra satelit untuk memantau sumber daya hutan yang memerlukan peninjauan lebih lanjut.

Adapun kesimpulan dan catatan khusus yang menjadi prioritas dalam pertimbangan ini adalah:

**Proposal ini harus diterima karena sangat sesuai dengan rencana kerja pemerintahan jangka panjang.** Meskipun terdapat kekurangan dalam kelengkapan dokumen dan potensi tumpang tindih, manfaat jangka panjang dari proposal ini sangat signifikan.

Demikian Berita Acara Hasil Evaluasi Proposal ini kami sampaikan untuk menjadi perhatian dan tindak lanjut sebagaimana mestinya.

---

Jakarta, 27 September 2025

Mengetahui,

<table style="width:100%; text-align:center; " border="0" cellspacing="0" cellpadding="6">
  <tr>
    <td>
        <div class="sig-head">Kepala Biro Sumber Daya Manusia dan Organisasi</div>
        <span class="ttd-space"><br><br></span>
        <div class="sig">
            <span class="nama">Dedy Asriady, S.Si., M.P.</span>
            <span class="nip">NIP. 197408182000031001</span>
        </div>
    </td>
    <td>
        <div class="sig-head">Direktur Inventarisasi dan Pemantauan Sumber Daya Hutan</div>
        <span class="ttd-space"><br><br></span>
        <div class="sig">
            <span class="nama">Dr. R Agus Budi Santosa, S.Hut, M.T.</span>
            <span class="nip">NIP. 196809201998031003</span>
        </div>
    </td>
  </tr>
  <tr class="rowspacer"><td colspan="2"><br></td></tr>
  <tr>
    <td>
        <div class="sig-head">Kepala Pusat Data dan Informasi</div>
        <span class="ttd-space"><br><br></span>
        <div class="sig">
            <span class="nama">Dr. Ishak Yassir, S.Hut., M.Si.</span>
            <span class="nip">NIP. 197305222000031003</span>
        </div>
    </td>
    <td>
        <div class="sig-head">Kepala Biro Perencanaan</div>
        <span class="ttd-space"><br><br></span>
        <div class="sig">
            <span class="nama">Dr. Edi Sulistyo Heri Susetyo, S.Hut., M.Si.</span>
            <span class="nip">NIP. 197012062000031004</span>
        </div>
    </td>
  </tr>
</table>

"""
        pdf_stream = md_to_pdf_xhtml2pdf(
            result.evaluasi_letter,
            title="Berita Acara Hasil Evaluasi Proposal",
            extra_css="""
                /* xhtml2pdf mendukung CSS dasar */
                .ttd-space { display:block; height:54pt; }
                .sig-head { font-size: 12px; text-align:center; font-weight: bold}
                .sig { line-height:1; text-align:center; }
                .sig .nama, .sig .nip, .sig .jabatan {
                    display:block;
                    margin:0;
                    padding:0;
                    }
                .sig .nama   { font-size: 11px; font-weight: bold; margin:0; padding:0;}
                .sig .nip     { font-size:11px; color:#333; margin-top:2pt; margin:0; padding:0;}
                .sig .jabatan { font-size:11px; margin-top:2pt; margin:0; padding:0;}

                /* Opsional: rapatkan sedikit antar-baris */
                /* .sig .nama   { margin-top: 2px; }   */
                /* @page margin via pisaPageSize kurang konsisten; pakai margin di body atau table spacing */
                """,
        )
        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Berita Acara Hasil Evaluasi Proposal.pdf",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))