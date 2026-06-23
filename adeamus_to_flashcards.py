#!/usr/bin/env python3
"""Convert an authorized Adeamus vocabulary PDF/text export into flashcard-ready XLSX.

Output columns (exact):
1) lektion
2) latein words
3) german explainations
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from openpyxl import Workbook


LESSON_PATTERNS = [
    re.compile(r"^\s*(lektion\s*\d+[a-z]?)\b", re.IGNORECASE),
    re.compile(r"^\s*(l\.?\s*\d+[a-z]?)\b", re.IGNORECASE),
]

# Common separators between latin and german columns in text exports.
ENTRY_SEPARATORS = [";", " - ", " – ", " — ", ":"]


@dataclass
class Row:
    lesson: str
    latin: str
    german: str


def read_pdf_text(input_path: Path, use_ocr: bool) -> List[str]:
    if use_ocr:
        return _read_pdf_text_ocr(input_path)
    return _read_pdf_text_native(input_path)


def _read_pdf_text_native(input_path: Path) -> List[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(input_path))
    pages: List[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return pages


def _read_pdf_text_ocr(input_path: Path) -> List[str]:
    from pdf2image import convert_from_path
    import pytesseract

    images = convert_from_path(str(input_path), dpi=300)
    pages: List[str] = []
    for image in images:
        pages.append(pytesseract.image_to_string(image, lang="deu+lat"))
    return pages


def read_text_export(input_path: Path) -> List[str]:
    # Text exports are treated as one logical page split by form feed markers if present.
    content = input_path.read_text(encoding="utf-8", errors="replace")
    return content.split("\f")


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def detect_lesson(line: str, current: str) -> str:
    for pattern in LESSON_PATTERNS:
        match = pattern.search(line)
        if match:
            return normalize_ws(match.group(1)).lower()
    return current


def split_entry(line: str) -> Optional[tuple[str, str]]:
    text = normalize_ws(line)
    if not text:
        return None

    # Skip obvious headers/footers/page numbers.
    if re.fullmatch(r"\d+", text):
        return None
    if len(text) < 3:
        return None

    for sep in ENTRY_SEPARATORS:
        if sep in text:
            left, right = text.split(sep, 1)
            left = normalize_ws(left)
            right = normalize_ws(right)
            if left and right:
                return left, right

    # Fallback: two or more spaces often represent column boundaries from copied PDFs.
    parts = [p.strip() for p in re.split(r"\s{2,}", text) if p.strip()]
    if len(parts) >= 2:
        left = parts[0]
        right = " ".join(parts[1:])
        if left and right:
            return left, right

    return None


def parse_pages(pages: Iterable[str]) -> List[Row]:
    rows: List[Row] = []
    current_lesson = "unknown"

    for page in pages:
        for raw_line in page.splitlines():
            line = normalize_ws(raw_line)
            if not line:
                continue

            current_lesson = detect_lesson(line, current_lesson)
            parsed = split_entry(line)
            if not parsed:
                continue

            latin, german = parsed

            # Skip lines that are probably not vocabulary entries.
            if latin.lower().startswith("lektion"):
                continue
            if german.lower().startswith("lektion"):
                continue

            rows.append(Row(lesson=current_lesson, latin=latin, german=german))

    return dedupe_rows(rows)


def dedupe_rows(rows: List[Row]) -> List[Row]:
    seen = set()
    out: List[Row] = []
    for row in rows:
        key = (row.lesson, row.latin, row.german)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def write_xlsx(rows: List[Row], output_path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "flashcards"

    ws.append(["lektion", "latein words", "german explainations"])
    for row in rows:
        ws.append([row.lesson, row.latin, row.german])

    for col in ("A", "B", "C"):
        ws.column_dimensions[col].width = 40

    wb.save(str(output_path))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract vocabulary entries from an authorized source file and produce .xlsx "
            "with columns: lektion, latein words, german explainations"
        )
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to authorized PDF/TXT source")
    parser.add_argument("--output", required=True, type=Path, help="Path to output XLSX")
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Use OCR for scanned PDFs (requires tesseract + poppler)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    ext = args.input.suffix.lower()
    if ext == ".pdf":
        pages = read_pdf_text(args.input, use_ocr=args.ocr)
    elif ext in {".txt", ".md"}:
        pages = read_text_export(args.input)
    else:
        raise SystemExit("Unsupported input format. Use .pdf, .txt, or .md")

    rows = parse_pages(pages)
    if not rows:
        raise SystemExit(
            "No vocabulary rows parsed. Try --ocr for scanned PDFs or provide a text-export source."
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_xlsx(rows, args.output)

    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
