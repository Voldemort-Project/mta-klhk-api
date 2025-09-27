# convert_xhtml2pdf.py
from io import BytesIO
from pathlib import Path
from jinja2 import Template
from markdown import markdown
from xhtml2pdf import pisa
from bs4 import BeautifulSoup

HTML_TEMPLATE = Path("template/evaluation_letter_template.html").read_text(encoding="utf-8")


def _force_bullets(html: str) -> str:
    """Flatten <ul>/<ol> to HTML with visible bullets/numbers for xhtml2pdf."""
    soup = BeautifulSoup(html, "html.parser")

    # Ubah <ul> -> div.list dan <li> -> div.li dengan bullet '•'
    for ul in soup.find_all("ul"):
        wrapper = soup.new_tag("div", **{"class": "list-ul"})
        for li in ul.find_all("li", recursive=False):
            item = soup.new_tag("div", **{"class": "li"})
            bullet = soup.new_tag("span", **{"class": "bullet"})
            bullet.string = ""  # U+2022
            text = soup.new_tag("span", **{"class": "txt"})
            # pindahkan isi li ke text
            for child in list(li.children):
                text.append(child.extract())
            item.append(bullet)
            item.append(text)
            wrapper.append(item)
        ul.replace_with(wrapper)

    # Ubah <ol> -> div.list-ol dan nomor manual 1., 2., ...
    for ol in soup.find_all("ol"):
        wrapper = soup.new_tag("div", **{"class": "list-ol"})
        idx = 1
        for li in ol.find_all("li", recursive=False):
            item = soup.new_tag("div", **{"class": "li"})
            bullet = soup.new_tag("span", **{"class": "bullet"})
            bullet.string = "•  "
            idx += 1
            text = soup.new_tag("span", **{"class": "txt"})
            for child in list(li.children):
                text.append(child.extract())
            item.append(bullet)
            item.append(text)
            wrapper.append(item)
        ol.replace_with(wrapper)

    # Sisipkan CSS minimal agar rapi
    style = soup.new_tag("style")
    style.string = """
    .list-ul, .list-ol { margin: 0 0 2pt 0; }
    .list-ul .li, .list-ol .li { position: relative; margin: 0 0 0pt 18px; }
    .list-ul .li .bullet, .list-ol .li .bullet {
        position: absolute; left: -14pt; top: 0; width: 12pt; display: inline-block;
    }
    .list-ul .li .txt, .list-ol .li .txt { display: inline; font-size: 11px; }
    """
    # taruh di head (atau prepend ke body jika tidak ada head)
    if soup.head:
        soup.head.append(style)
    else:
        soup.insert(0, style)

    return str(soup)


def md_to_pdf_xhtml2pdf(
    md_text: str,
    title="Dokumen",
    extra_css: str | None = None,
    force_bullets: bool = True,
) -> BytesIO:
    ROOT_DIR = Path(__file__).resolve().parent.parent.parent
    kop_path = ROOT_DIR / "assets" / "kop_surat_2.png"
    watermark_path = ROOT_DIR / "assets" / "logo-simpatik-6.png"
    body_html = markdown(
        md_text, extensions=["extra", "sane_lists"], output_format="html5"
    )

    final_html = Template(HTML_TEMPLATE).render(
        title=title,
        extra_css=extra_css or "",
        content=body_html,
        kop_src=str(kop_path),
        watermark_src=str(watermark_path),
    )

    if force_bullets:
        final_html = _force_bullets(final_html)

    # Path("debug_after_force.html").write_text(final_html, encoding="utf-8")

    pdf_bytes = BytesIO()
    result = pisa.CreatePDF(src=final_html, dest=pdf_bytes, encoding="utf-8")
    if result.err:
        raise RuntimeError("Gagal membuat PDF (xhtml2pdf).")
    pdf_bytes.seek(0)
    return pdf_bytes

    # with open(output_pdf_path, "wb") as f:
    #     result = pisa.CreatePDF(src=final_html, dest=f, encoding="utf-8")
    # if result.err:
    #     raise RuntimeError("Gagal membuat PDF (xhtml2pdf).")
    # print(f"✅ PDF tersimpan: {output_pdf_path}")


# if __name__ == "__main__":
#     sample_md = r"""
# ## Berita Acara Hasil Evaluasi Proposal

# Nomor: KM/2025/BA/SPBE/1

# Telah dilakukan evaluasi terhadap proposal dengan rincian sebagai berikut:

# - Judul Proposal: {rincian_output}
# - Pengusul: {direktorat}
# - Estimasi Biaya: Rp. {total_biaya}
# - Tanggal Pengajuan: {current_date}

# Evaluasi ini dilakukan untuk memastikan kesesuaian proposal dengan SOP Budget Clearance, kelengkapan dokumen, keselarasan rencana dan tugas fungsi serta menghindari potensi tumpang tindih dengan kegiatan lainnya.

# Ringkasan Kajian adalah sebagai berikut:

# 1. Isi Temuan Satu
# 2. Isi Temuan Dua

# Adapun kesimpulan dan catatan khusus yang menjadi prioritas dalam pertimbangan ini adalah:

# Berikan catatan khusus dari user_remarks, jika ada. Jika tidak ada, maka tulis "Tidak ada catatan khusus.". Berikan kesimpulan singkat 1-2 kalimat


# Demikian Berita Acara Hasil Evaluasi Proposal ini kami sampaikan untuk menjadi perhatian dan tindak lanjut sebagaimana mestinya.

# ---

# Jakarta, 27 September 2025

# <table style="width:100%; text-align:center; " border="0" cellspacing="0" cellpadding="6">
#   <tr>
#     <td>
#         <div class="sig-head">Kepala Biro Sumber Daya Manusia dan Organisasi</div>
#         <span class="ttd-space"><br><br></span>
#         <div class="sig">
#             <span class="nama">Dedy Asriady, S.Si., M.P.</span>
#             <span class="nip">NIP. 197408182000031001</span>
#         </div>
#     </td>
#     <td>
#         <div class="sig-head">Direktur Inventarisasi dan Pemantauan Sumber Daya Hutan</div>
#         <span class="ttd-space"><br><br></span>
#         <div class="sig">
#             <span class="nama">Dr. R Agus Budi Santosa, S.Hut, M.T.</span>
#             <span class="nip">NIP. 196809201998031003</span>
#         </div>
#     </td>
#   </tr>
#   <tr class="rowspacer"><td colspan="2"><br></td></tr>
#   <tr>
#     <td>
#         <div class="sig-head">Kepala Pusat Data dan Informasi</div>
#         <span class="ttd-space"><br><br></span>
#         <div class="sig">
#             <span class="nama">Dr. Ishak Yassir, S.Hut., M.Si.</span>
#             <span class="nip">NIP. 197305222000031003</span>
#         </div>
#     </td>
#     <td>
#         <div class="sig-head">Kepala Biro Perencanaan</div>
#         <span class="ttd-space"><br><br></span>
#         <div class="sig">
#             <span class="nama">Dr. Edi Sulistyo Heri Susetyo, S.Hut., M.Si.</span>
#             <span class="nip">NIP. 197012062000031004</span>
#         </div>
#     </td>
#   </tr>
# </table>
# """
#     sample_md = r"""
# ## Berita Acara Hasil Evaluasi Proposal

# Nomor: KM/2025/BA/SPBE/1

# <table>
#     <tr>
#         <td style="width: 30%;">Judul Proposal</td>
#         <td>: Data dan Peta Kondisi Sumber Daya Hutan dan Kawasan Hutan</td>
#     </tr>
#     <tr>
#         <td style="width: 30%;">Pengusul</td>
#         <td>: Direktorat Inventarisasi dan Pemantauan Sumber Daya Hutan</td>
#     </tr>
#     <tr>
#         <td style="width: 30%;">Estimasi Biaya</td>
#         <td>: Rp. 950.000.000</td>
#     </tr>
#     <tr>
#         <td style="width: 30%;">Tanggal Pengajuan</td>
#         <td>: 27 September 2025</td>
#     </tr>
# </table>


# Evaluasi ini dilakukan untuk memastikan kesesuaian proposal dengan SOP Budget Clearance, kelengkapan dokumen, keselarasan rencana dan tugas fungsi serta menghindari potensi tumpang tindih dengan kegiatan lainnya.

# Ringkasan Kajian adalah sebagai berikut:

# 1. Proposal yang diajukan oleh Direktorat Inventarisasi dan Pemantauan Sumber Daya Hutan dengan judul "Data dan Peta Kondisi Sumber Daya Hutan dan Kawasan Hutan" dinilai relevan dengan KRO Belanja Data (BMA/QMA).
# 2. Penilaian oleh *assessor* menunjukkan keselarasan yang kuat (skor 85) dengan agenda strategis Kementerian LHK, terutama dalam Tata Ruang dan Pengelolaan Wilayah, serta Pemanfaatan IPTEK dan Peningkatan SDM LHK. Proposal ini mendukung inventarisasi dan pemantauan sumber daya hutan.
# 3. Proposal belum menyertakan dokumen pendukung yang dipersyaratkan seperti Kerangka Acuan Kerja (KAK) yang lengkap, Dokumen Arsitektur SPBE Domain Data dan Informasi, Rujukan regulasi dalam melakukan Kegiatan Pendataan minimum Data prioritas, Surat Rekomendasi BPS (jika relevan), dan Daftar Data (Formulir isian daftar data).
# 4. Terdapat potensi tumpang tindih dengan program pemantauan SDH (skor 35 dan 60), khususnya dalam penggunaan data citra satelit untuk memantau sumber daya hutan yang memerlukan peninjauan lebih lanjut.

# Adapun kesimpulan dan catatan khusus yang menjadi prioritas dalam pertimbangan ini adalah:

# **Proposal ini harus diterima karena sangat sesuai dengan rencana kerja pemerintahan jangka panjang.** Meskipun terdapat kekurangan dalam kelengkapan dokumen dan potensi tumpang tindih, manfaat jangka panjang dari proposal ini sangat signifikan.

# Demikian Berita Acara Hasil Evaluasi Proposal ini kami sampaikan untuk menjadi perhatian dan tindak lanjut sebagaimana mestinya.

# ---

# Jakarta, 27 September 2025

# Mengetahui,

# <table style="width:100%; text-align:center; " border="0" cellspacing="0" cellpadding="6">
#   <tr>
#     <td>
#         <div class="sig-head">Kepala Biro Sumber Daya Manusia dan Organisasi</div>
#         <span class="ttd-space"><br><br></span>
#         <div class="sig">
#             <span class="nama">Dedy Asriady, S.Si., M.P.</span>
#             <span class="nip">NIP. 197408182000031001</span>
#         </div>
#     </td>
#     <td>
#         <div class="sig-head">Direktur Inventarisasi dan Pemantauan Sumber Daya Hutan</div>
#         <span class="ttd-space"><br><br></span>
#         <div class="sig">
#             <span class="nama">Dr. R Agus Budi Santosa, S.Hut, M.T.</span>
#             <span class="nip">NIP. 196809201998031003</span>
#         </div>
#     </td>
#   </tr>
#   <tr class="rowspacer"><td colspan="2"><br></td></tr>
#   <tr>
#     <td>
#         <div class="sig-head">Kepala Pusat Data dan Informasi</div>
#         <span class="ttd-space"><br><br></span>
#         <div class="sig">
#             <span class="nama">Dr. Ishak Yassir, S.Hut., M.Si.</span>
#             <span class="nip">NIP. 197305222000031003</span>
#         </div>
#     </td>
#     <td>
#         <div class="sig-head">Kepala Biro Perencanaan</div>
#         <span class="ttd-space"><br><br></span>
#         <div class="sig">
#             <span class="nama">Dr. Edi Sulistyo Heri Susetyo, S.Hut., M.Si.</span>
#             <span class="nip">NIP. 197012062000031004</span>
#         </div>
#     </td>
#   </tr>
# </table>

# """
#     md_to_pdf_xhtml2pdf(
#         md_text=sample_md,
#         output_pdf_path="berita_acara.pdf",
#         title="Berita Acara Hasil Evaluasi Proposal",
#         extra_css="""
#           /* xhtml2pdf mendukung CSS dasar */
#           .ttd-space { display:block; height:54pt; }
#           .sig-head { font-size: 12px; text-align:center; font-weight: bold}
#           .sig { line-height:1; text-align:center; }
#           .sig .nama, .sig .nip, .sig .jabatan {
#             display:block;
#             margin:0;
#             padding:0;
#             }
#           .sig .nama   { font-size: 11px; font-weight: bold; margin:0; padding:0;}
#           .sig .nip     { font-size:11px; color:#333; margin-top:2pt; margin:0; padding:0;}
#           .sig .jabatan { font-size:11px; margin-top:2pt; margin:0; padding:0;}

#           /* Opsional: rapatkan sedikit antar-baris */
#           /* .sig .nama   { margin-top: 2px; }   */
#           /* @page margin via pisaPageSize kurang konsisten; pakai margin di body atau table spacing */
#         """,
#     )
