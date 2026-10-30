from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from core import DAYS, VERSION, ExtractionError, apply_page_edits, extract_pdf, render_page, validate_result
from exports import build_exports

st.set_page_config(page_title="JadualPDF | Pengekstrak Jadual Guru", page_icon="📄", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
[data-testid="stMainBlockContainer"]{max-width:1550px;padding-top:3.8rem}
h1{letter-spacing:-1px!important}h2{letter-spacing:-.4px!important}
[data-testid="stMetric"]{background:white;border:1px solid #dde7e8;border-radius:12px;padding:15px 20px}
[data-testid="stMetricLabel"]{color:#607581}[data-testid="stMetricValue"]{font-size:2rem}
[data-testid="stSidebar"]{background:#eaf0f0}.eyebrow{font-size:11px;letter-spacing:2px;font-weight:700;color:#13685f;margin-bottom:8px}
.lead{color:#607581;font-size:16px;max-width:850px;line-height:1.65}.source-note{color:#607581;font-size:12px}
[data-testid="stFileUploader"]{border-radius:12px}.stTabs [data-baseweb="tab-list"]{gap:20px}
</style>""", unsafe_allow_html=True)


def clear_export():
    st.session_state.pop("downloads", None)
    st.session_state.pop("download_revision", None)


def current_result():
    return st.session_state.get("result")


with st.sidebar:
    st.markdown("### JadualPDF")
    st.caption(f"Pengekstrak jadual guru · v{VERSION}")
    st.markdown("**1. Upload PDF**\n\n**2. Semak dan betulkan**\n\n**3. Muat turun untuk relief**")
    st.divider()
    st.markdown("**Format versi pertama**")
    st.caption("Jadual aSc dengan petak bergaris, lima hari Isnin–Jumaat dan ringkasan jumlah bagi setiap guru. PDF imbasan memerlukan OCR dan belum disokong.")
    st.caption("Fail diproses di komputer yang menjalankan app. Tiada kunci API AI diperlukan.")
    st.divider()
    if current_result():
        if st.button("Kosongkan sesi", width="stretch"):
            for key in list(st.session_state):
                del st.session_state[key]
            st.rerun()
    st.caption("Selepas memuat turun, gunakan menu Import jadual dalam Sistem Relief 1.1.")

st.markdown('<div class="eyebrow">DARIPADA PDF KEPADA DATA YANG BOLEH DISEMAK</div>', unsafe_allow_html=True)
st.title("Jadual guru, sedia untuk relief.")
st.markdown('<p class="lead">Muat naik jadual waktu PDF, semak petak asal bersama hasil bacaan, kemudian eksport Excel, CSV atau JSON.</p>', unsafe_allow_html=True)

with st.container(border=True):
    upload_col, action_col = st.columns([3, 1], vertical_alignment="bottom")
    with upload_col:
        uploaded = st.file_uploader("Pilih PDF jadual waktu guru", type=["pdf"], key="upload_pdf", help="Maksimum 20 MB dan 150 halaman. Jadual PDF teks asli sahaja untuk versi pertama.")
    with action_col:
        extract_clicked = st.button("Ekstrak jadual", type="primary", width="stretch", disabled=uploaded is None)
    if uploaded:
        uploaded_data = uploaded.getvalue()
        new_hash = hashlib.sha256(uploaded_data).hexdigest()
        if st.session_state.get("upload_hash") != new_hash:
            for key in ("result", "pdf_bytes", "downloads", "image_cache", "export_ack", "review_reason", "revision", "page_picker", "block_picker"):
                st.session_state.pop(key, None)
            st.session_state["upload_hash"] = new_hash
        st.caption(f"{uploaded.name} · {len(uploaded_data)/1024:.0f} KB · Semakan jumlah dan bacaan teks kedua akan dijalankan.")
    if extract_clicked and uploaded:
        with st.status("Mengekstrak petak dan menyemak teks PDF…", expanded=True) as status:
            bar = st.progress(0, text="Membuka PDF…")
            try:
                result = extract_pdf(uploaded_data, uploaded.name,
                                     progress=lambda n, total: bar.progress(n/total, text=f"Halaman {n} daripada {total}"))
                check = validate_result(result)
                st.session_state.update(result=result, pdf_bytes=uploaded_data, revision=0, image_cache={})
                clear_export()
                status.update(label="Ekstraksi selesai. Semak hasil di bawah." if not check["blockers"] else "Ekstraksi selesai dengan halaman/data yang perlu diperiksa.", state="complete", expanded=False)
            except ExtractionError as e:
                status.update(label="PDF belum dapat diproses.", state="error", expanded=True)
                st.error(str(e))
            except Exception:
                status.update(label="Pemprosesan tidak selesai.", state="error", expanded=True)
                st.error("Pemprosesan tidak selesai. Cuba fail PDF asal yang tidak berkunci. Tiada data daripada sesi ini dieksport.")

result = current_result()
if not result:
    st.info("Mulakan dengan PDF jadual guru. Hasil bacaan tidak dimasukkan ke Google Sheet secara automatik; cikgu menyemak dan memuat turun dahulu.")
    st.stop()

check = validate_result(result)
if st.session_state.pop("saved_notice", False):
    st.success("Pembetulan disimpan dalam sesi ini. Semakan dikira semula; jana semula fail eksport selepas menyemak.")
metrics = st.columns(4)
for column, title, value in zip(metrics, ("Halaman dibaca", "Guru", "Waktu pengajaran", "Perlu perhatian"),
                                 (f"{check['supported_pages']}/{result['page_count']}", check["teachers"], check["lessons"], check["blockers"]+check["reviews"])):
    column.metric(title, value)
st.caption(f"{result['filename']} · {check['blocks']:,} petak sumber · ID guru ialah ID sumber bagi fail ini, bukan identiti kekal merentas edisi.")

review_tab, report_tab, download_tab = st.tabs(["Semak & betulkan", "Laporan semakan", "Muat turun"])
with review_tab:
    page_numbers = list(range(1, result["page_count"]+1))
    def page_label(n):
        report = result["pages"][n-1]
        return f"{n:02} · {report['teacher'] or 'Halaman tidak disokong'}"
    page_no = st.selectbox("Halaman / guru", page_numbers, format_func=page_label, key="page_picker")
    page = result["pages"][page_no-1]
    source_col, edit_col = st.columns([1.05, 1.25], gap="large")
    with source_col:
        st.subheader("Petak asal PDF")
        blocks = [b for b in result["blocks"] if b["halaman_pdf"] == page_no]
        block_ids = [""] + [b["blok_id"] for b in blocks]
        block_map = {b["blok_id"]: b for b in blocks}
        selected = st.selectbox("Sorot petak sumber", block_ids,
                                format_func=lambda k: "Semua petak" if not k else f"{block_map[k]['hari']} · {block_map[k]['subjek_label']} · {block_map[k]['kelas_label']} · {k}",
                                key=f"block_picker_{page_no}")
        cache = st.session_state["image_cache"]
        image_key = (page_no, selected)
        if image_key not in cache:
            if len(cache) >= 6:
                cache.pop(next(iter(cache)))
            cache[image_key] = render_page(st.session_state["pdf_bytes"], page_no, blocks, selected)
        st.image(cache[image_key], width="stretch")
        if selected:
            image = Image.open(io.BytesIO(cache[image_key]))
            box = block_map[selected]["bbox"]
            crop = (max(0, int(box[0]*1.6)-8), max(0, int(box[1]*1.6)-8), min(image.width, int(box[2]*1.6)+8), min(image.height, int(box[3]*1.6)+8))
            st.caption("Petak dipilih — pembesaran")
            st.image(image.crop(crop), width="stretch")
        st.caption("Hijau: petak yang diekstrak. Jingga: petak dipilih. Paparan ini kekal sebagai sumber asal sebelum pembetulan.")
    with edit_col:
        st.subheader("Data pengajaran")
        rows = [r for r in result["rows"] if r["halaman_pdf"] == page_no]
        if not page["supported"]:
            st.error("Profil halaman ini tidak disokong. Semak Laporan semakan. Eksport relief disekat supaya halaman tidak tercicir secara senyap.")
        elif not rows:
            st.info("Tiada waktu pengajaran pada halaman ini.")
        else:
            st.caption("Hari: 1=Isnin, 2=Selasa, 3=Rabu, 4=Khamis, 5=Jumaat. Simpan pembetulan sebelum bertukar halaman.")
            conflicts = [i for i in check["issues"] if i["kod"] == "PERTINDIHAN" and i["halaman_pdf"] == page_no]
            if conflicts:
                st.warning("Ada waktu bertindih pada halaman ini. Bandingkan dua baris berikut dengan PDF sebelum membuat pembetulan.")
                for item in conflicts:
                    st.write(item["mesej"])
                st.caption("Nombor baris ialah baris dalam keseluruhan data ekstrak. Cari nombor yang sama dalam lajur Baris data di bawah. Jika PDF juga bertindih, semak dengan penyelaras jadual; jangan ubah masa semata-mata untuk melepasi semakan.")
            teacher = next(t for t in result["teachers"] if t["halaman_pdf"] == page_no)
            fields = ["rekod_id", "hari_no", "waktu", "masa_mula", "masa_tamat", "subjek_label", "kelas_label", "bilik_label"]
            with st.form(f"page_form_{page_no}_{st.session_state['revision']}"):
                name = st.text_input("Nama guru", teacher["nama_guru"], max_chars=150)
                frame = pd.DataFrame([{f: r[f] for f in fields} for r in rows])
                global_rows = {r["rekod_id"]: i for i, r in enumerate(result["rows"], 1)}
                frame.insert(1, "baris_data", [global_rows[r["rekod_id"]] for r in rows])
                edited = st.data_editor(frame, hide_index=True, num_rows="fixed", width="stretch", height=min(650, 85+len(rows)*35),
                                        disabled=["rekod_id", "baris_data"], column_config={
                                            "rekod_id": None,
                                            "baris_data": st.column_config.NumberColumn("Baris data", format="%d"),
                                            "hari_no": st.column_config.NumberColumn("Hari", min_value=1, max_value=5, step=1, required=True),
                                            "waktu": st.column_config.NumberColumn("Waktu", min_value=1, max_value=30, step=1, required=True),
                                            "masa_mula": st.column_config.TextColumn("Mula", required=True, validate=r"^([01]\d|2[0-3]):[0-5]\d$"),
                                            "masa_tamat": st.column_config.TextColumn("Tamat", required=True, validate=r"^([01]\d|2[0-3]):[0-5]\d$"),
                                            "subjek_label": st.column_config.TextColumn("Subjek", required=True),
                                            "kelas_label": st.column_config.TextColumn("Kelas", required=True),
                                            "bilik_label": st.column_config.TextColumn("Bilik")}, key=f"editor_{page_no}_{st.session_state['revision']}")
                save = st.form_submit_button("Simpan pembetulan", type="primary")
            if save:
                try:
                    edited_records = edited.fillna("").to_dict("records")
                    updated = apply_page_edits(result, page_no, edited_records, name)
                    st.session_state["result"] = updated
                    st.session_state["revision"] += 1
                    st.session_state["saved_notice"] = True
                    st.session_state.pop("export_ack", None)
                    clear_export()
                    st.rerun()
                except (TypeError, ValueError, KeyError) as e:
                    st.error(str(e))
            tcheck = next(t for t in check["teacher_checks"] if t["guru_id"] == teacher["guru_id"])
            st.caption(f"Jumlah PDF: {tcheck['jumlah_waktu_pdf']} · Jumlah data: {tcheck['jumlah_waktu_ekstrak']} · Semakan teks petak asal: {page['text_checks']-page['text_failures']}/{page['text_checks']} sepadan.")

with report_tab:
    st.subheader("Semakan automatik")
    if check["blockers"]:
        st.error(f"{check['blockers']} ralat penghalang. Eksport relief belum dibenarkan.")
    elif check["reviews"]:
        st.warning(f"{check['reviews']} perkara perlu disemak. Baca sumber dan catat sebab pengesahan sebelum eksport.")
    else:
        st.success(f"Semua jumlah guru dan subjek sepadan. {sum(p['text_checks'] for p in result['pages'])} petak asal telah dibandingkan antara dua pembaca PDF.")
    st.caption("Semakan mengesahkan struktur, pertindihan, jumlah serta aksara petak asal. Ia tidak mengesahkan jadual sekolah masih berkuat kuasa. Pembetulan pengguna direkod berasingan.")
    if check["issues"]:
        st.dataframe(pd.DataFrame(check["issues"])[["tahap", "kod", "halaman_pdf", "mesej"]], hide_index=True, width="stretch")
    conflicts = [i for i in check["issues"] if i["kod"] == "PERTINDIHAN"]
    if conflicts:
        st.markdown("#### Butiran waktu bertindih")
        conflict_columns = ["halaman_pdf", "hari", "baris_a", "waktu_a", "masa_a", "kelas_a", "subjek_a", "baris_b", "waktu_b", "masa_b", "kelas_b", "subjek_b", "julat_bertindih"]
        st.dataframe(pd.DataFrame(conflicts)[conflict_columns], hide_index=True, width="stretch")
        st.info("Buka tab Semak & betulkan, pilih halaman yang dilaporkan dan cari nombor Baris data. Semak hari serta masa kedua-dua baris pada PDF asal.")
    st.markdown("#### Jumlah setiap guru")
    st.dataframe(pd.DataFrame(check["teacher_checks"]), hide_index=True, width="stretch")
    with st.expander(f"Jumlah mengikut subjek ({len(check['subject_checks'])} semakan)"):
        st.dataframe(pd.DataFrame(check["subject_checks"]), hide_index=True, width="stretch")
    if result["edits"]:
        st.caption(f"{len(result['edits'])} perubahan baris telah disimpan. Rujukan asal tidak ditindih.")
    conflict_ids = {i.get(k) for i in conflicts for k in ("rekod_a", "rekod_b")}
    diagnostic_data = json.dumps({"versi": VERSION, "sumber": result["filename"], "sha256": result["sha256"], "semakan": check,
                                  "halaman": result["pages"], "pembetulan": result["edits"],
                                  "baris_bermasalah": [r for r in result["rows"] if r["rekod_id"] in conflict_ids]}, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button("Muat turun laporan diagnostik", diagnostic_data, "laporan_semakan.json", "application/json")

with download_tab:
    st.subheader("Fail untuk sistem relief")
    st.write("Excel mempunyai tab Jadual dan Guru yang diperlukan oleh importer. CSV dan JSON mengandungi data pengajaran yang sama.")
    if check["blockers"]:
        st.error("Eksport relief disekat. Tiada fail separa yang dilabel lengkap akan dijana. Laporan diagnostik masih boleh dimuat turun.")
    else:
        export_key = f"{result['sha256'][:12]}_{st.session_state['revision']}"
        if check["reviews"]:
            st.warning("Hasil mempunyai perbezaan yang perlu disahkan. Fail eksport akan mencatat status DISAHKAN PENGGUNA, bukannya semua semakan lulus.")
            reason = st.text_area("Catatan pengesahan perbezaan (sekurang-kurangnya 10 aksara)", key=f"review_reason_{export_key}", on_change=clear_export)
        else:
            reason = ""
        acknowledged = st.checkbox("Saya telah menyemak data dan label kelas/subjek gabungan sebelum eksport.", key=f"export_ack_{export_key}", on_change=clear_export)
        if st.button("Sediakan fail eksport", type="primary", disabled=not acknowledged or (bool(check["reviews"]) and len(reason.strip()) < 10)):
            with st.spinner("Menyediakan Excel, CSV dan JSON…"):
                try:
                    st.session_state["downloads"] = build_exports(result, confirmed=True, review_reason=reason)
                    st.session_state["download_revision"] = st.session_state["revision"]
                except ValueError as e:
                    st.error(str(e))
        files = st.session_state.get("downloads")
        if files and st.session_state.get("download_revision") == st.session_state["revision"] and acknowledged:
            st.success("Fail sedia dimuat turun. Gunakan fail ini melalui menu Import jadual dalam Sistem Relief 1.1.")
            c1, c2, c3, c4 = st.columns(4)
            c1.download_button("Excel (.xlsx)", files["xlsx"], "jadual.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
            c2.download_button("CSV (.csv)", files["csv"], "Jadual.csv", "text/csv", width="stretch")
            c3.download_button("JSON (.json)", files["json"], "data_relief.json", "application/json", width="stretch")
            c4.download_button("Semua fail (.zip)", files["zip"], "data-jadual.zip", "application/zip", width="stretch")
    st.caption("Pembahagian guru bagi subjek/kelas gabungan tidak diteka. Importer relief akan meminta padanan nama kepada ID guru kekal.")
