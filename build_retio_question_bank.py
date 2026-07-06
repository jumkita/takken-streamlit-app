import csv
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

import easyocr
import fitz
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
URLS_PATH = DATA_DIR / "retio_pdf_urls.txt"
OUT_CSV = DATA_DIR / "user_question_bank.csv"
LOG_PATH = DATA_DIR / "retio_extract_log.txt"


RIGHTS = "権利関係"
LAW = "法令上の制限"
BROKER = "宅建業法"
TAX = "税・その他"


def normalize_url(url: str) -> str:
    p = urllib.parse.urlsplit(url.strip())
    path = urllib.parse.quote(urllib.parse.unquote(p.path))
    query = urllib.parse.quote_plus(urllib.parse.unquote_plus(p.query), safe="=&")
    return urllib.parse.urlunsplit((p.scheme, p.netloc, path, query, p.fragment))


def safe_filename_from_url(url: str) -> str:
    name = urllib.parse.unquote(Path(urllib.parse.urlsplit(url).path).name).strip()
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    name = re.sub(r"\s+", "", name)
    name = name.replace("　", "")
    return name


def exam_tag_from_name(name: str) -> str:
    stem = Path(name).stem
    stem = urllib.parse.unquote(stem).replace("　", "")
    return re.sub(r"[^A-Za-z0-9]+", "", stem).upper() or "UNK"


def download_pdf(url: str, dst: Path) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(
            normalize_url(url),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.retio.or.jp/exam/past_ques_ans/other/",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            dst.write_bytes(res.read())
        return True, "downloaded"
    except Exception as e:
        return False, f"download failed: {e}"


def text_clean(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\u3000", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return s


def compact(s: str) -> str:
    s = text_clean(s)
    lines = []
    for ln in s.split("\n"):
        t = ln.strip()
        if re.fullmatch(r"\d{1,2}", t):
            continue
        lines.append(t)
    s = " ".join([x for x in lines if x])
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_questions(full_text: str) -> list[dict]:
    marker_re = re.compile(r"(?:^|\n)\s*[【〔]?\s*問\s*([0-9]{1,2})(?:\s*[】〕])?", re.MULTILINE)
    marks = list(marker_re.finditer(full_text))
    rows = []
    for i, m in enumerate(marks):
        qno = int(m.group(1))
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(full_text)
        block = full_text[start:end]

        # 選択肢1〜4の開始位置を探す（改行 + 数字）
        opt_re = re.compile(r"(?:^|\n)\s*([1-4])\s+")
        opts = list(opt_re.finditer(block))
        if len(opts) < 4:
            # OCRで「1」が落ちるケースに対応（2,3,4 がある場合）
            digits = [int(x.group(1)) for x in opts]
            if len(opts) >= 3 and 2 in digits and 3 in digits and 4 in digits:
                pseudo = re.match(r"", block)
                assert pseudo is not None
                opts = [pseudo] + [x for x in opts if int(x.group(1)) in (2, 3, 4)]
            else:
                continue

        stem = compact(block[: opts[0].start()])
        choices = []
        for j in range(4):
            o_start = opts[j].end() if hasattr(opts[j], "end") else 0
            o_end = opts[j + 1].start() if j + 1 < 4 else len(block)
            choices.append(compact(block[o_start:o_end]))

        if not stem or any(not c for c in choices):
            continue
        rows.append({"qno": qno, "question": stem, "choices": choices})
    return rows


def parse_answers(full_text: str, qnos: list[int]) -> list[int]:
    q_count = len(qnos)
    cleaned = text_clean(full_text)
    lines = [ln.strip() for ln in cleaned.split("\n")]

    # 1) 行単位で 1~4 のみ
    one_digit = [ln for ln in lines if re.fullmatch(r"[1-4]", ln)]
    if len(one_digit) >= q_count:
        return [int(x) - 1 for x in one_digit[-q_count:]]

    # 2) 「問 1 3」のようなペア
    pairs = re.findall(r"問\s*([0-9]{1,2})\s*([1-4])", cleaned)
    if pairs:
        amap = {}
        for q, a in pairs:
            amap[int(q)] = int(a) - 1
        if all(q in amap for q in qnos):
            return [amap[q] for q in qnos]

    # 3) 正解番号表以降の数字列
    pos = cleaned.find("正解番号表")
    tail = cleaned[pos:] if pos >= 0 else cleaned[-12000:]
    nums = re.findall(r"(?<!\d)([1-4])(?!\d)", tail)
    if len(nums) >= q_count:
        return [int(x) - 1 for x in nums[-q_count:]]
    return []


def field_by_qno(qno: int) -> str:
    if qno <= 14:
        return RIGHTS
    if qno <= 22:
        return LAW
    if qno <= 25:
        return TAX
    if qno <= 45:
        return BROKER
    return TAX


def year_tag_from_name(name: str) -> str:
    m = re.search(r"(R[0-9]+|H[0-9]{1,2}|S[0-9]{1,2})", name, re.IGNORECASE)
    return m.group(1).upper() if m else "UNK"


def era_sort_key(year_tag: str) -> tuple[int, int]:
    m = re.match(r"([RHS])(\d+)", year_tag)
    if not m:
        return (9, 999)
    era = {"S": 0, "H": 1, "R": 2}[m.group(1)]
    num = int(m.group(2))
    return (era, num)


def extract_text_with_ocr(doc: fitz.Document, reader: easyocr.Reader) -> str:
    page_indices = list(range(min(doc.page_count, 26)))
    for i in range(max(doc.page_count - 3, 0), doc.page_count):
        if i not in page_indices:
            page_indices.append(i)

    texts = []
    for i in page_indices:
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        parts = reader.readtext(img, detail=0, paragraph=False, workers=0)
        texts.append("\n".join(parts))
    return "\n".join(texts)


def parse_pdf_text_only(full_text: str) -> tuple[list[dict], list[int]]:
    qs = parse_questions(full_text)
    if not qs:
        return [], []
    qnos = [q["qno"] for q in qs]
    answers = parse_answers(full_text, qnos)
    return qs, answers


def is_good_result(qs: list[dict], answers: list[int]) -> bool:
    # OCR年度は取りこぼしが出るため、40問以上かつ正解数一致を採用基準とする
    return len(qs) >= 40 and len(answers) == len(qs)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    if not URLS_PATH.exists():
        raise SystemExit(f"URL一覧がありません: {URLS_PATH}")

    urls = [ln.strip().lstrip("\ufeff") for ln in URLS_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    max_pdfs = int(os.getenv("MAX_PDFS", "0") or "0")
    use_ocr = os.getenv("USE_OCR", "0") == "1"
    if max_pdfs > 0:
        urls = urls[:max_pdfs]
    all_rows = []
    logs = []
    reader = None

    for url in urls:
        pdf_name = safe_filename_from_url(url)
        pdf_path = PDF_DIR / pdf_name
        year_tag = year_tag_from_name(pdf_name)
        exam_tag = exam_tag_from_name(pdf_name)
        print(f"[START] {pdf_name}", flush=True)

        if not pdf_path.exists():
            ok, msg = download_pdf(url, pdf_path)
            logs.append(f"{pdf_name}: {msg}")
            if not ok:
                continue
        else:
            logs.append(f"{pdf_name}: already exists")

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logs.append(f"{pdf_name}: open failed ({e})")
            continue

        # 1) テキストレイヤー抽出
        full_text = "\n".join(page.get_text() for page in doc)
        qs, answers = parse_pdf_text_only(full_text)
        method = "text"

        # 2) 不十分ならOCR抽出
        if use_ocr and not is_good_result(qs, answers):
            if reader is None:
                logs.append("easyocr: initializing reader (ja,en)")
                print("[INFO] initializing OCR reader", flush=True)
                reader = easyocr.Reader(["ja", "en"], gpu=False, verbose=False)
            try:
                ocr_text = extract_text_with_ocr(doc, reader)
                qs2, answers2 = parse_pdf_text_only(ocr_text)
                if is_good_result(qs2, answers2):
                    qs, answers = qs2, answers2
                    method = "ocr"
            except Exception as e:
                logs.append(f"{pdf_name}: ocr failed ({e})")

        if not is_good_result(qs, answers):
            logs.append(f"{pdf_name}: parse failed q={len(qs)} ans={len(answers)}")
            print(f"[SKIP] {pdf_name} q={len(qs)} ans={len(answers)}", flush=True)
            continue

        for i, q in enumerate(qs):
            all_rows.append(
                {
                    "id": f"{exam_tag}_Q{q['qno']:02d}",
                    "field": field_by_qno(q["qno"]),
                    "year": year_tag,
                    "difficulty": 2,
                    "question": q["question"],
                    "choice1": q["choices"][0],
                    "choice2": q["choices"][1],
                    "choice3": q["choices"][2],
                    "choice4": q["choices"][3],
                    "answer": answers[i],
                    "explanation": f"公式解答: {answers[i] + 1}",
                    "source_url": url,
                }
            )

        logs.append(f"{pdf_name}: parsed {len(qs)} questions ({method})")
        print(f"[OK] {pdf_name} q={len(qs)} method={method}", flush=True)

    if not all_rows:
        raise SystemExit("抽出結果が0件でした。")

    def sort_key(r: dict) -> tuple:
        q = int(re.search(r"_Q(\d+)$", r["id"]).group(1))
        return era_sort_key(r["year"]), r["id"].split("_Q")[0], q

    all_rows.sort(key=sort_key)

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "field",
                "year",
                "difficulty",
                "question",
                "choice1",
                "choice2",
                "choice3",
                "choice4",
                "answer",
                "explanation",
                "source_url",
            ],
        )
        writer.writeheader()
        writer.writerows(all_rows)

    LOG_PATH.write_text("\n".join(logs), encoding="utf-8")
    print(f"rows={len(all_rows)}")
    print(f"csv={OUT_CSV}")
    print(f"log={LOG_PATH}")


if __name__ == "__main__":
    main()
