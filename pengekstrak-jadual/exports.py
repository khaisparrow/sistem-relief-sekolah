"""Eksport aplikasi: nilai siap baca, serasi importer Sistem Relief 1.1."""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile

import xlsxwriter

from core import VERSION, clock, minute, validate_result

JADUAL_HEADERS = ["jadual_id", "guru_id", "nama_guru", "hari_no", "hari", "waktu", "masa_mula", "masa_tamat",
                  "subjek_label", "kelas_label", "bilik_label", "blok_id", "halaman_pdf"]


def csv_bytes(headers, rows):
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(headers)
    for row in rows:
        values = []
        for v in row:
            if isinstance(v, str) and re.match(r"^\s*[=+@-]", v):
                v = "'" + v
            values.append(v)
        writer.writerow(values)
    return out.getvalue().encode("utf-8-sig")


def build_tables(result, check, review_reason=""):
    tables = {}
    add = lambda name, heads, rows: tables.__setitem__(name, [heads] + rows)
    add("Jadual", JADUAL_HEADERS, [[r[h] for h in JADUAL_HEADERS] for r in result["rows"]])
    teacher_heads = ["guru_id", "nama_guru", "halaman_pdf", "jumlah_waktu_pdf", "jumlah_waktu_ekstrak", "beza", "status_semakan", "aktif"]
    add("Guru", teacher_heads, [[t["guru_id"], t["nama_guru"], t["halaman_pdf"], t["jumlah_waktu_pdf"],
                                t["jumlah_waktu_ekstrak"], t["beza"], t["status"], "YA"] for t in check["teacher_checks"]])
    headers = result["pages"][0]["headers"] if result["pages"] else []
    add("Waktu", ["susunan_pdf", "label_waktu", "masa_mula", "masa_tamat", "jenis"],
        [[i+1, h["label"], h["start"], h["end"], "PENGAJARAN" if h["label"].isdigit() else "REHAT"] for i, h in enumerate(headers)])
    bh = ["blok_id", "guru_id", "nama_guru", "hari", "waktu_mula", "waktu_akhir", "bil_waktu", "halaman_pdf", "petak_pdf", "subjek_teks_asal", "kelas_teks_asal", "bilik_teks_asal", "semakan_teks"]
    add("BlokAsal", bh, [[b["blok_id"], b["guru_id"], b["nama_guru"], b["hari"], b["slots"][0]["waktu"], b["slots"][-1]["waktu"], len(b["slots"]), b["halaman_pdf"],
                         ",".join(f"{v:.3f}" for v in b["bbox"]), b["subjek_asal"], b["kelas_asal"], b["bilik_asal"], "SEPADAN" if b["teks_sepadan"] else "SEMAK"] for b in result["blocks"]])
    th = ["guru_id", "nama_guru", "halaman_pdf", "jumlah_waktu_pdf", "jumlah_subjek_pdf", "jumlah_waktu_ekstrak", "beza", "status"]
    add("SemakanGuru", th, [[r[k] for k in th] for r in check["teacher_checks"]])
    sh = ["guru_id", "nama_guru", "halaman_pdf", "subjek_pdf", "jumlah_waktu_pdf", "jumlah_waktu_ekstrak", "beza", "status"]
    add("SemakanSubjek", sh, [[r[k] for k in sh] for r in check["subject_checks"]])
    metadata = [
        ["Sumber", result["filename"]], ["SHA256 sumber", result["sha256"]], ["Versi penghurai", VERSION],
        ["Masa ekstraksi (UTC)", result["created"]], ["Profil", result["profile"]],
        ["Halaman disokong", f"{check['supported_pages']}/{result['page_count']}"],
        ["Jumlah guru", check["teachers"]], ["Jumlah waktu", check["lessons"]], ["Petak sumber", check["blocks"]],
        ["Semakan", "SEMAK - DISAHKAN PENGGUNA" if check["reviews"] else "LULUS DENGAN PEMBETULAN PENGGUNA" if result["edits"] else "LULUS"],
        ["Bilangan rekod pembetulan", len(result["edits"])], ["Catatan pengesahan semakan", review_reason],
        ["Rujukan BlokAsal", "Teks dan petak asal sebelum pembetulan. Jadual mengandungi data terkini selepas pembetulan."],
        ["Label gabungan", "Dikekalkan sebagai kumpulan; pembahagian guru kepada subjek atau kelas tidak diteka."],
        ["Identiti guru", "ID sumber berdasarkan halaman dalam fail ini. Importer relief memadankan kepada ID kekal."],
        ["Waktu bertindih", "Gunakan masa sebenar; nombor waktu berbeza mungkin bertindih. Rehat bukan waktu pengajaran."],
        ["Skop semakan", "Padanan jumlah dan teks asal tidak mengesahkan bahawa jadual sekolah masih berkuat kuasa."],
        ["Import relief", "Excel: pilih fail ini dalam Import jadual. CSV: pilih Jadual.csv. JSON: pilih data_relief.json."],
    ]
    add("Catatan", ["perkara", "keterangan"], metadata)
    if result["edits"]:
        add("Pembetulan", ["rekod_id", "halaman_pdf", "sebelum_json", "selepas_json"],
            [[e["rekod_id"], e["halaman_pdf"], json.dumps(e["sebelum"], ensure_ascii=False), json.dumps(e["selepas"], ensure_ascii=False)] for e in result["edits"]])
    return tables


def excel_bytes(tables):
    out = io.BytesIO()
    book = xlsxwriter.Workbook(out, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
    body = book.add_format({"font_name": "Arial", "font_size": 10, "font_color": "#243247", "valign": "vcenter"})
    header = book.add_format({"font_name": "Arial", "font_size": 10, "bold": True, "bg_color": "#25476A", "font_color": "white", "text_wrap": True, "valign": "vcenter", "align": "center"})
    time_format = book.add_format({"font_name": "Arial", "font_size": 10, "num_format": "hh:mm", "valign": "vcenter"})
    wrapped = book.add_format({"font_name": "Arial", "font_size": 10, "valign": "top", "text_wrap": True})
    for name, data in tables.items():
        sheet = book.add_worksheet(name)
        sheet.hide_gridlines(2)
        sheet.freeze_panes(1, 2 if name not in ("Catatan", "Waktu") else 0)
        sheet.set_default_row(22)
        sheet.set_row(0, 34)
        for c, h in enumerate(data[0]):
            width = 18
            if h == "nama_guru": width = 58
            elif h in ("kelas_label", "kelas_teks_asal", "subjek_pdf"): width = 55
            elif h == "keterangan": width = 110
            elif h == "perkara": width = 30
            elif "json" in h: width = 75
            elif "teks_asal" in h: width = 28
            elif h.startswith("jumlah_"): width = 24
            elif h == "petak_pdf": width = 38
            sheet.set_column(c, c, width)
            sheet.write_string(0, c, h, header)
        if name != "Catatan":
            sheet.autofilter(0, 0, len(data)-1, len(data[0])-1)
        for r, values in enumerate(data[1:], 1):
            max_lines = 1
            for c, value in enumerate(values):
                h = data[0][c]
                if h in ("masa_mula", "masa_tamat") and isinstance(value, str) and re.fullmatch(r"\d{2}:\d{2}", value):
                    sheet.write_number(r, c, minute(value)/1440, time_format)
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    sheet.write_number(r, c, value, body)
                elif isinstance(value, bool):
                    sheet.write_boolean(r, c, value, body)
                else:
                    text = "" if value is None else str(value)
                    fmt = wrapped if "teks_asal" in h or "json" in h or name == "Catatan" else body
                    sheet.write_string(r, c, text, fmt)
                    if fmt is wrapped:
                        max_lines = max(max_lines, len(text.splitlines()), (len(text)//110+1) if name == "Catatan" else 1)
            if max_lines > 1:
                sheet.set_row(r, max_lines*14+8)
    book.close()
    return out.getvalue()


def build_exports(result, confirmed=False, review_reason=""):
    check = validate_result(result)
    if check["blockers"]:
        raise ValueError("Eksport relief disekat kerana halaman atau data masih mempunyai ralat penghalang.")
    if not confirmed:
        raise ValueError("Sahkan semakan data sebelum menjana fail eksport.")
    if check["reviews"] and len(review_reason.strip()) < 10:
        raise ValueError("Catat sebab pengesahan sekurang-kurangnya 10 aksara untuk hasil yang memerlukan semakan.")
    tables = build_tables(result, check, review_reason)
    xlsx = excel_bytes(tables)
    data = {"versi": VERSION, "sumber": result["filename"], "sha256": result["sha256"],
            "guru": [dict(zip(tables["Guru"][0], r)) for r in tables["Guru"][1:]],
            "jadual": [{h: r[h] for h in JADUAL_HEADERS} for r in result["rows"]],
            "semakan": {"status": "DISAHKAN_PENGGUNA" if check["reviews"] else "LULUS_DENGAN_PEMBETULAN" if result["edits"] else "LULUS", "catatan": review_reason, "isu": check["issues"], "bil_pembetulan": len(result["edits"])},
            "pembetulan": result["edits"],
            "waktu": [dict(zip(tables["Waktu"][0], r)) for r in tables["Waktu"][1:]]}
    json_data = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    main_csv = csv_bytes(tables["Jadual"][0], tables["Jadual"][1:])
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("jadual.xlsx", xlsx)
        for name, table in tables.items():
            z.writestr(name+".csv", csv_bytes(table[0], table[1:]))
        z.writestr("data_relief.json", json_data)
        z.writestr("laporan_semakan.json", json.dumps({"semakan": check, "pembetulan": result["edits"]}, ensure_ascii=False, indent=2))
        z.writestr("BACA_DAHULU.txt", "Data daripada "+result["filename"]+"\nImport ke Sistem Relief 1.1 melalui jadual.xlsx, Jadual.csv atau data_relief.json.\nID guru ialah ID sumber; semak padanan semasa import.\nBlokAsal ialah rujukan sebelum pembetulan.\n")
    return {"xlsx": xlsx, "csv": main_csv, "json": json_data, "zip": zipped.getvalue()}
