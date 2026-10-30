"""Penghurai jadual aSc PDF teks. Tiada AI/OCR atau panggilan rangkaian."""
from __future__ import annotations

import copy
import hashlib
import io
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

import pdfplumber
import pypdfium2 as pdfium

VERSION = "1.0.1"
DAYS = ["Isnin", "Selasa", "Rabu", "Khamis", "Jumaat"]
SUBJECTS = {
    "BM": "BAHASA MELAYU", "BI": "BAHASA INGGERIS", "MM": "MATEMATIK",
    "MT": "MATEMATIK TAMBAHAN", "PJ": "PENDIDIKAN JASMANI",
    "PK": "PENDIDIKAN KESIHATAN", "SEJ": "SEJARAH", "PA": "PRINSIP AKAUN",
    "GEO": "GEOGRAFI", "PSV": "PENDIDIKAN SENI VISUAL", "BIO": "BIOLOGI",
    "SN": "SAINS", "RBT": "REKABENTUK TEKNOLOGI", "PSI": "PEND SYARIAH ISLAMIAH",
    "ASK": "ASAS SAINS KOMPUTER", "SK": "SAINS KOMPUTER", "PN": "PERNIAGAAN",
    "KIM": "KIMIA", "FZ": "FIZIK", "EK": "EKONOMI", "EKO": "EKONOMI",
    "BA": "BAHASA ARAB", "PQS": "PENDIDIKAN AL QURAN DAN AS SUNNAH",
    "SS": "SAINS SUKAN", "PI": "PENDIDIKAN ISLAM", "KKQ": "KELAS KEMAHIRAN AL QURAN",
    "PI/PM": "PI/PM", "PI/BC/BT": "PI/BC/BT", "BC/BT": "BC/BT", "PMPBD": "PMPBD",
}


class ExtractionError(ValueError):
    pass


class UnsupportedLayout(ExtractionError):
    pass


def inside(word, box):
    return (box[0] - .05 <= (word["x0"] + word["x1"]) / 2 < box[2] + .05
            and box[1] - .05 <= (word["top"] + word["bottom"]) / 2 < box[3] + .05)


def text_lines(words):
    rows = []
    for w in sorted(words, key=lambda w: (round(w["top"], 1), w["x0"])):
        if not rows or abs(rows[-1][0] - w["top"]) > 2:
            rows.append([w["top"], []])
        rows[-1][1].append(w)
    return [" ".join(w["text"] for w in sorted(ws, key=lambda w: w["x0"])) for _, ws in rows]


def join_label(parts):
    s = ""
    for p in parts:
        p = p.strip()
        if s and not s.endswith("/") and not p.startswith("/"):
            s += "/"
        s += p
    return s.replace(" ", "")


def minute(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,2}:\d{2}", value):
        raise ValueError("Masa mesti dalam format HH:mm.")
    h, m = map(int, value.split(":"))
    if h > 23 or m > 59:
        raise ValueError("Masa di luar julat.")
    return h * 60 + m


def clock(value):
    m = minute(str(value))
    return f"{m // 60:02}:{m % 60:02}"


def compact(value):
    return re.sub(r"[^A-Z]", "", str(value).upper())


def subject_name(code):
    code = str(code).replace(" ", "").upper()
    if code in SUBJECTS:
        return SUBJECTS[code]
    parts = code.split("/")
    return "/".join(SUBJECTS.get(p, p) for p in parts)


def diagnostic(severity, code, message, page=0):
    return {"tahap": severity, "kod": code, "halaman_pdf": page, "mesej": message}


def find_layout(page, words):
    cells = sorted(set(c for t in page.find_tables() for c in t.cells))
    if not cells:
        raise UnsupportedLayout("Garisan petak jadual tidak dikesan.")
    day_cells = {}
    # Pada teks diputar, pdfplumber melaporkan 'size' mengikut lebar glif.
    # Jangan pecahkan perkataan hari berdasarkan atribut fon/saiz.
    day_words = page.extract_words()
    for c in cells:
        ws = [w for w in day_words if inside(w, c)]
        if not ws or any(w["upright"] for w in ws):
            continue
        text = re.sub(r"\s+", "", "".join(w["text"] for w in ws)).lower()
        for i, name in enumerate(DAYS, 1):
            if text in (name.lower(), name.lower()[::-1]):
                if i in day_cells:
                    raise UnsupportedLayout("Label hari berganda; susun atur tidak dikenali.")
                day_cells[i] = c
    if set(day_cells) != {1, 2, 3, 4, 5}:
        raise UnsupportedLayout("Lima baris hari Isnin hingga Jumaat tidak dapat dipadankan.")
    ordered = [day_cells[i] for i in range(1, 6)]
    if ordered != sorted(ordered, key=lambda c: c[1]):
        raise UnsupportedLayout("Susunan hari tidak dikenali.")
    left, top, bottom = ordered[0][2], ordered[0][1], ordered[-1][3]
    subject = next((w for w in words if w["text"].lower() == "subjek" and w["top"] < top), None)
    count = next((w for w in words if w["text"].lower() == "jumlah" and w["top"] < top), None)
    if not subject or not count:
        raise UnsupportedLayout("Header ringkasan Subjek/Jumlah tidak ditemui.")
    subject_cell = next((c for c in cells if inside(subject, c)), None)
    count_cell = next((c for c in cells if inside(count, c)), None)
    if not subject_cell or not count_cell:
        raise UnsupportedLayout("Sempadan ringkasan tidak ditemui.")
    right, count_left = subject_cell[0], count_cell[0]
    headers = []
    for c in cells:
        if c[0] < left - .5 or c[2] > right + .5 or abs(c[3] - top) > .8:
            continue
        ws = [w for w in words if inside(w, c)]
        times = sorted([w for w in ws if re.fullmatch(r"\d{1,2}:\d{2}", w["text"])], key=lambda w: w["top"])
        label = "".join(w["text"] for w in ws if w not in times).strip()
        if len(times) != 2 or not (label.isdigit() or label.upper().startswith("RT")):
            raise UnsupportedLayout("Header waktu tidak dapat dibaca dengan pasti.")
        start, end = (clock(w["text"]) for w in times)
        if minute(start) >= minute(end):
            raise UnsupportedLayout("Julat masa pada header tidak sah.")
        headers.append({"box": list(c), "label": label, "start": start, "end": end})
    headers.sort(key=lambda h: h["box"][0])
    if not 5 <= len(headers) <= 40 or abs(headers[0]["box"][0] - left) > 1 or abs(headers[-1]["box"][2] - right) > 1:
        raise UnsupportedLayout("Header waktu tidak lengkap.")
    for a, b in zip(headers, headers[1:]):
        if abs(a["box"][2] - b["box"][0]) > 1:
            raise UnsupportedLayout("Terdapat jurang pada header waktu.")
    labels = [h["label"] for h in headers]
    if len(set(labels)) != len(labels):
        raise UnsupportedLayout("Label waktu berganda.")
    return {"cells": cells, "days": day_cells, "left": left, "right": right,
            "top": top, "bottom": bottom, "count_left": count_left, "headers": headers}


def printed_controls(page, words, layout, page_no, teacher_id):
    right = layout["right"]
    footer_words = [w for w in words if w["x0"] >= right and "Pelajaran/Minggu" in w["text"]]
    if len(footer_words) != 1:
        raise UnsupportedLayout("Jumlah Pelajaran/Minggu tidak dapat dikenal pasti.")
    footer_y = footer_words[0]["top"]
    total_words = [w for w in words if w["x0"] > layout["count_left"] and w["text"].isdigit()
                   and abs(w["top"] - footer_y) < 2]
    if len(total_words) != 1:
        raise UnsupportedLayout("Angka jumlah waktu mingguan tidak dapat dibaca.")
    total = int(total_words[0]["text"])
    chars = [c for c in page.chars if c["x0"] >= right and layout["top"] <= c["top"] < footer_y - 2]
    groups = []
    for c in chars:
        g = next((g for g in groups if abs(g[0] - c["top"]) < .5), None)
        if g is None:
            g = [c["top"], []]
            groups.append(g)
        g[1].append(c)
    controls = []
    for _, group in sorted(groups):
        digits = [c for c in group if c["x0"] > layout["count_left"] and c["text"].isdigit()]
        if not digits:
            continue
        label = "".join(c["text"] for c in group if c not in digits).strip()
        value = "".join(c["text"] for c in digits)
        if not label or not value.isdigit():
            raise UnsupportedLayout("Ringkasan subjek tidak lengkap.")
        controls.append({"guru_id": teacher_id, "halaman_pdf": page_no,
                         "subjek_pdf": label, "jumlah_pdf": int(value)})
    if not controls:
        raise UnsupportedLayout("Ringkasan subjek tiada.")
    return total, controls


def extract_pdf(data: bytes, filename="jadual.pdf", progress=None):
    if not data or len(data) > 20 * 1024 * 1024:
        raise ExtractionError("Pilih PDF yang sah, maksimum 20 MB.")
    if not data.lstrip().startswith(b"%PDF-"):
        raise ExtractionError("Fail ini bukan dokumen PDF yang sah.")
    result = {"version": VERSION, "filename": filename, "sha256": hashlib.sha256(data).hexdigest(),
              "created": datetime.now(timezone.utc).isoformat(), "profile": "aSc: Isnin-Jumaat, petak bergaris, ringkasan guru",
              "teachers": [], "blocks": [], "rows": [], "controls": [], "pages": [], "issues": [], "edits": []}
    try:
        pdf = pdfplumber.open(io.BytesIO(data))
        independent = pdfium.PdfDocument(data)
    except Exception as e:
        raise ExtractionError("PDF tidak dapat dibuka. Semak fail rosak atau perlindungan kata laluan.") from e
    try:
        if not 1 <= len(pdf.pages) <= 150:
            raise ExtractionError("Versi ini menerima 1 hingga 150 halaman PDF.")
        result["page_count"] = len(pdf.pages)
        teacher_names = set()
        for page_no, page in enumerate(pdf.pages, 1):
            if progress:
                progress(page_no, len(pdf.pages))
            report = {"page": page_no, "teacher_id": f"G{page_no:03}", "teacher": "", "supported": False,
                      "expected": None, "headers": [], "text_checks": 0, "text_failures": 0,
                      "width": page.width, "height": page.height}
            result["pages"].append(report)
            try:
                words = page.extract_words(extra_attrs=["fontname", "size"])
                if not page.chars:
                    raise UnsupportedLayout("Halaman berupa imej atau tiada teks. OCR belum tersedia dalam versi ini.")
                text = page.extract_text() or ""
                title = re.search(r"Jadual Waktu:\s*([^\n]+)", text, re.I)
                if not title:
                    raise UnsupportedLayout("Tajuk Jadual Waktu: NAMA GURU tidak ditemui.")
                teacher = title.group(1).strip()
                if teacher.casefold() in teacher_names:
                    raise UnsupportedLayout("Nama guru berulang pada beberapa halaman. Semak PDF yang mengandungi salinan berganda.")
                layout = find_layout(page, words)
                total, controls = printed_controls(page, words, layout, page_no, report["teacher_id"])
                report.update(teacher=teacher, expected=total, headers=layout["headers"])
                blocks = []
                used = Counter()
                for c in layout["cells"]:
                    if c[0] < layout["left"] - .5 or c[2] > layout["right"] + .5 or c[1] < layout["top"] - .5 or c[3] > layout["bottom"] + .5:
                        continue
                    items = [(i, w) for i, w in enumerate(words) if inside(w, c) and w["upright"]]
                    if not items:
                        continue
                    day = next((d for d, b in layout["days"].items() if abs(b[1] - c[1]) < 1 and abs(b[3] - c[3]) < 1), None)
                    hs = [h for h in layout["headers"] if h["box"][0] >= c[0] - .5 and h["box"][2] <= c[2] + .5]
                    if day is None or not hs or any(not h["label"].isdigit() for h in hs):
                        raise UnsupportedLayout("Petak berteks tidak dapat dipadankan kepada hari/waktu pengajaran.")
                    ws = [w for _, w in items]
                    scale = 595.32 / page.height
                    subj = [w for w in ws if w["fontname"].endswith("F2") or w["size"] * scale > 10]
                    normal = [w for w in ws if w not in subj]
                    classes = [w for w in normal if re.search(r"[1-6](?:KAA|[A-Z]{1,5})", w["text"])]
                    room = [w for w in normal if w not in classes]
                    if not subj or not classes:
                        raise UnsupportedLayout("Fon/label subjek atau kelas tidak serasi dengan profil penghurai.")
                    subject = join_label(text_lines(subj))
                    if subject == "PMP/BD":
                        subject = "PMPBD"
                    blocks.append({"guru_id": report["teacher_id"], "nama_guru": teacher, "hari_no": day, "hari": DAYS[day-1],
                                   "subjek_label": subject, "kelas_label": join_label(text_lines(classes)),
                                   "bilik_label": ",".join(text_lines(room)), "halaman_pdf": page_no, "bbox": list(c),
                                   "subjek_asal": "\n".join(text_lines(subj)), "kelas_asal": "\n".join(text_lines(classes)),
                                   "bilik_asal": "\n".join(text_lines(room)),
                                   "slots": [{"waktu": int(h["label"]), "masa_mula": h["start"], "masa_tamat": h["end"]} for h in hs]})
                    used.update(i for i, _ in items)
                grid_words = [i for i, w in enumerate(words) if w["upright"] and layout["left"] < (w["x0"]+w["x1"])/2 < layout["right"]
                              and layout["top"] < (w["top"]+w["bottom"])/2 < layout["bottom"]]
                if any(used[i] != 1 for i in grid_words):
                    raise UnsupportedLayout("Sebahagian teks jadual tidak dipadankan tepat satu kali kepada petak.")
                blocks.sort(key=lambda b: (b["hari_no"], b["slots"][0]["waktu"]))
                for n, b in enumerate(blocks, 1):
                    b["blok_id"] = f"{report['teacher_id']}-B{n:02}"
                check_page_text(independent, page_no-1, blocks, report)
                report["supported"] = True
                teacher_names.add(teacher.casefold())
                result["teachers"].append({"guru_id": report["teacher_id"], "nama_guru": teacher, "halaman_pdf": page_no, "jumlah_pdf": total})
                result["controls"].extend(controls)
                result["blocks"].extend(blocks)
                for b in blocks:
                    for si, slot in enumerate(b["slots"]):
                        row = {k: b[k] for k in ("guru_id", "nama_guru", "hari_no", "hari", "subjek_label", "kelas_label", "bilik_label", "halaman_pdf", "blok_id")}
                        row.update(slot)
                        row["rekod_id"] = f"{b['blok_id']}-S{si+1}"
                        row["jadual_id"] = f"{b['guru_id']}-H{b['hari_no']}-W{slot['waktu']:02}"
                        result["rows"].append(row)
            except UnsupportedLayout as e:
                result["issues"].append(diagnostic("HALANG", "SUSUN_ATUR", str(e), page_no))
            except Exception as e:
                result["issues"].append(diagnostic("HALANG", "BACA_HALAMAN", f"Halaman gagal dibaca ({type(e).__name__}).", page_no))
    finally:
        pdf.close()
        independent.close()
    return result


def check_page_text(document, index, blocks, report):
    p = document[index]
    t = p.get_textpage()
    try:
        height = p.get_height()
        chars = []
        for i in range(t.count_chars()):
            left, bottom, right, top = t.get_charbox(i)
            chars.append(((left+right)/2, height-(bottom+top)/2, t.get_text_range(i, 1)))
        clean = lambda s: Counter(c for c in s if not c.isspace())
        for b in blocks:
            left, top, right, bottom = b["bbox"]
            actual = "".join(c for x, y, c in chars if left <= x < right and top <= y < bottom)
            expected = b["subjek_asal"] + b["kelas_asal"] + b["bilik_asal"]
            b["teks_sepadan"] = clean(actual) == clean(expected)
            report["text_checks"] += 1
            report["text_failures"] += int(not b["teks_sepadan"])
    finally:
        t.close()
        p.close()


def validate_result(result):
    issues = copy.deepcopy(result["issues"])
    rows = result["rows"]
    known = {t["guru_id"]: t for t in result["teachers"]}
    seen = set()
    intervals = defaultdict(list)
    clocks = {}
    teacher_counts = Counter()
    subject_counts = Counter()
    for i, row in enumerate(rows, 1):
        page = row.get("halaman_pdf", 0)
        try:
            teacher = row["guru_id"]
            day = int(row["hari_no"])
            period = int(row["waktu"])
            if float(row["hari_no"]) != day or float(row["waktu"]) != period or not 1 <= day <= 5 or not 1 <= period <= 30 or teacher not in known:
                raise ValueError("Guru, hari atau nombor waktu tidak sah.")
            start, end = minute(row["masa_mula"]), minute(row["masa_tamat"])
            if start >= end or end-start > 180:
                raise ValueError("Masa tamat mesti selepas mula; maksimum 180 minit satu waktu.")
            for field, limit in (("subjek_label", 250), ("kelas_label", 500)):
                if not isinstance(row.get(field), str) or not row[field].strip() or len(row[field]) > limit:
                    raise ValueError("Subjek dan kelas wajib diisi dengan teks.")
            if not isinstance(row.get("bilik_label"), str) or len(row["bilik_label"]) > 150:
                raise ValueError("Label bilik mesti teks, maksimum 150 aksara.")
            if row.get("hari") != DAYS[day-1] or row.get("nama_guru") != known[teacher]["nama_guru"]:
                raise ValueError("Label hari atau nama guru tidak sepadan dengan daftar.")
            key = (teacher, day, period)
            if key in seen:
                raise ValueError("Guru mempunyai waktu berganda pada hari sama.")
            seen.add(key)
            if period in clocks and clocks[period] != (start, end):
                raise ValueError("Nombor waktu sama mempunyai masa berlainan; tidak serasi import relief.")
            clocks[period] = (start, end)
            intervals[teacher, day].append((start, end, i))
            teacher_counts[teacher] += 1
            subject_counts[teacher, compact(subject_name(row["subjek_label"]))] += 1
        except (KeyError, TypeError, ValueError, OverflowError) as e:
            issues.append(diagnostic("HALANG", "DATA_BARIS", f"Baris {i}: {e}", page))
    if not rows:
        issues.append(diagnostic("HALANG", "TIADA_DATA", "Tiada waktu pengajaran yang boleh dieksport."))
    if len(rows) > 20000:
        issues.append(diagnostic("HALANG", "HAD_IMPORT", "Melebihi had 20,000 waktu bagi importer relief."))
    for t in result["teachers"]:
        if not t["nama_guru"].strip() or len(t["nama_guru"]) > 150:
            issues.append(diagnostic("HALANG", "NAMA_GURU", "Nama guru kosong atau melebihi 150 aksara.", t["halaman_pdf"]))
    for (teacher, day), slots in intervals.items():
        slots.sort()
        active = []
        for b in slots:
            active = [a for a in active if a[1] > b[0]]
            for a in active:
                ra, rb = rows[a[2]-1], rows[b[2]-1]
                time_a = f"{clock(ra['masa_mula'])}-{clock(ra['masa_tamat'])}"
                time_b = f"{clock(rb['masa_mula'])}-{clock(rb['masa_tamat'])}"
                overlap = f"{max(a[0],b[0])//60:02}:{max(a[0],b[0])%60:02}-{min(a[1],b[1])//60:02}:{min(a[1],b[1])%60:02}"
                issue = diagnostic("HALANG", "PERTINDIHAN",
                                   f"{known[teacher]['nama_guru']}, {DAYS[day-1]}: baris {a[2]} (waktu {ra['waktu']}, {ra['kelas_label']}, {time_a}) "
                                   f"bertindih dengan baris {b[2]} (waktu {rb['waktu']}, {rb['kelas_label']}, {time_b}). Julat bertindih: {overlap}.", known[teacher]["halaman_pdf"])
                issue.update(hari=DAYS[day-1], baris_a=a[2], rekod_a=ra["rekod_id"], blok_a=ra["blok_id"], waktu_a=ra["waktu"],
                             masa_a=time_a, kelas_a=ra["kelas_label"], subjek_a=ra["subjek_label"],
                             baris_b=b[2], rekod_b=rb["rekod_id"], blok_b=rb["blok_id"], waktu_b=rb["waktu"],
                             masa_b=time_b, kelas_b=rb["kelas_label"], subjek_b=rb["subjek_label"], julat_bertindih=overlap)
                issues.append(issue)
            active.append(b)
    teacher_checks, subject_checks = [], []
    expected_subject = Counter()
    for c in result["controls"]:
        expected_subject[c["guru_id"], compact(c["subjek_pdf"])] += c["jumlah_pdf"]
    for t in result["teachers"]:
        actual = teacher_counts[t["guru_id"]]
        expected = t["jumlah_pdf"]
        source_sum = sum(c["jumlah_pdf"] for c in result["controls"] if c["guru_id"] == t["guru_id"])
        match = actual == expected == source_sum
        teacher_checks.append({"guru_id": t["guru_id"], "nama_guru": t["nama_guru"], "halaman_pdf": t["halaman_pdf"],
                               "jumlah_waktu_pdf": expected, "jumlah_subjek_pdf": source_sum, "jumlah_waktu_ekstrak": actual,
                               "beza": actual-expected, "status": "SEPADAN" if match else "SEMAK"})
        if not match:
            issues.append(diagnostic("SEMAK", "JUMLAH_GURU", f"{t['nama_guru']}: data {actual}, jumlah PDF {expected}, ringkasan subjek {source_sum}.", t["halaman_pdf"]))
    used_subject_keys = set()
    for c in result["controls"]:
        key = (c["guru_id"], compact(c["subjek_pdf"]))
        if key in used_subject_keys:
            continue
        used_subject_keys.add(key)
        actual, expected = subject_counts[key], expected_subject[key]
        subject_checks.append({"guru_id": c["guru_id"], "nama_guru": known[c["guru_id"]]["nama_guru"], "halaman_pdf": c["halaman_pdf"],
                               "subjek_pdf": c["subjek_pdf"], "jumlah_waktu_pdf": expected, "jumlah_waktu_ekstrak": actual,
                               "beza": actual-expected, "status": "SEPADAN" if actual == expected else "SEMAK"})
        if actual != expected:
            issues.append(diagnostic("SEMAK", "JUMLAH_SUBJEK", f"{c['subjek_pdf']}: data {actual}, PDF {expected}.", c["halaman_pdf"]))
    for key, count in subject_counts.items():
        if key not in expected_subject:
            issues.append(diagnostic("SEMAK", "SUBJEK_TIDAK_DIPADAN", f"Label subjek {key[1]} ({count} waktu) tidak dipadankan kepada ringkasan PDF.", known[key[0]]["halaman_pdf"]))
    for p in result["pages"]:
        if p["text_failures"]:
            issues.append(diagnostic("SEMAK", "TEKS_SUMBER", f"{p['text_failures']} petak tidak sepadan antara dua pembaca PDF. Semak imej sumber.", p["page"]))
    return {"issues": issues, "teacher_checks": teacher_checks, "subject_checks": subject_checks,
            "blockers": sum(i["tahap"] == "HALANG" for i in issues), "reviews": sum(i["tahap"] == "SEMAK" for i in issues),
            "teachers": len(known), "lessons": len(rows), "blocks": len(result["blocks"]),
            "supported_pages": sum(p["supported"] for p in result["pages"])}


def apply_page_edits(result, page_no, edited_rows, teacher_name):
    candidate = copy.deepcopy(result)
    teacher = next((t for t in candidate["teachers"] if t["halaman_pdf"] == page_no), None)
    if not teacher or not isinstance(teacher_name, str) or not teacher_name.strip() or len(teacher_name) > 150:
        raise ValueError("Nama guru mesti diisi (maksimum 150 aksara).")
    name = teacher_name.strip()
    if any(t["guru_id"] != teacher["guru_id"] and t["nama_guru"].casefold() == name.casefold() for t in candidate["teachers"]):
        raise ValueError("Nama guru ini sudah digunakan pada halaman lain.")
    originals = [r for r in candidate["rows"] if r["halaman_pdf"] == page_no]
    if len(edited_rows) != len(originals) or {r["rekod_id"] for r in edited_rows} != {r["rekod_id"] for r in originals}:
        raise ValueError("Identiti atau bilangan baris berubah. Versi ini menyokong pembetulan baris sedia ada.")
    indexed = {r["rekod_id"]: r for r in edited_rows}
    changes = []
    for row in candidate["rows"]:
        if row["halaman_pdf"] != page_no:
            continue
        old = copy.deepcopy(row)
        edit = indexed[row["rekod_id"]]
        for field in ("hari_no", "waktu", "masa_mula", "masa_tamat", "subjek_label", "kelas_label", "bilik_label"):
            row[field] = edit[field]
        row["hari_no"] = int(row["hari_no"]) if float(row["hari_no"]).is_integer() else row["hari_no"]
        row["waktu"] = int(row["waktu"]) if float(row["waktu"]).is_integer() else row["waktu"]
        if not isinstance(row["hari_no"], int) or not 1 <= row["hari_no"] <= 5 or not isinstance(row["waktu"], int) or not 1 <= row["waktu"] <= 30:
            raise ValueError("Hari mesti 1-5 dan waktu mesti 1-30, tanpa pecahan.")
        row["masa_mula"], row["masa_tamat"] = clock(row["masa_mula"]), clock(row["masa_tamat"])
        row["hari"], row["nama_guru"] = DAYS[row["hari_no"]-1], name
        row["jadual_id"] = f"{row['guru_id']}-H{row['hari_no']}-W{row['waktu']:02}"
        if old != row:
            changes.append({"rekod_id": row["rekod_id"], "halaman_pdf": page_no, "sebelum": old, "selepas": copy.deepcopy(row)})
    teacher["nama_guru"] = name
    check = validate_result(candidate)
    if check["blockers"] > validate_result(result)["blockers"]:
        messages = [i["mesej"] for i in check["issues"] if i["tahap"] == "HALANG"]
        raise ValueError("Pembetulan tidak disimpan: " + " ".join(messages[:3]))
    candidate["edits"].extend(changes)
    return candidate


def render_page(data, page_no, blocks=None, selected_block="", scale=1.6):
    from PIL import ImageDraw
    doc = pdfium.PdfDocument(data)
    page = doc[page_no-1]
    try:
        image = page.render(scale=scale).to_pil().convert("RGB")
        draw = ImageDraw.Draw(image)
        for b in blocks or []:
            if b["halaman_pdf"] != page_no:
                continue
            box = tuple(round(v*scale) for v in b["bbox"])
            color = "#e38c24" if b["blok_id"] == selected_block else "#247c69"
            draw.rectangle(box, outline=color, width=4 if b["blok_id"] == selected_block else 2)
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()
    finally:
        page.close()
        doc.close()
