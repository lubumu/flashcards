# Adeamus Latin-German Flashcard Extractor

This project creates an Excel file with exactly 3 columns:

1. `lektion`
2. `latein words`
3. `german explainations`

## Important

Use this only with an authorized source file that you are allowed to process.

## Setup (macOS)

```bash
cd /Users/vw2ix71/Documents/Projekte/lateinAdemas
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For scanned PDFs (OCR mode), install OCR dependencies:

```bash
brew install tesseract poppler
```

## Usage

### 1) Native text PDF

```bash
python adeamus_to_flashcards.py \
  --input ./Adeamus-Gesamtwortschatz-1.pdf \
  --output ./out/adeamus_flashcards.xlsx
```

### 2) Scanned PDF (OCR)

```bash
python adeamus_to_flashcards.py \
  --input ./Adeamus-Gesamtwortschatz-1.pdf \
  --output ./out/adeamus_flashcards.xlsx \
  --ocr
```

### 3) Text export

```bash
python adeamus_to_flashcards.py \
  --input ./Adeamus-Gesamtwortschatz-1.txt \
  --output ./out/adeamus_flashcards.xlsx
```

## Notes

- The parser uses heuristics for lesson detection and vocabulary splitting.
- If your source has a different layout, adapt `ENTRY_SEPARATORS` and lesson regex in `adeamus_to_flashcards.py`.
- Output workbook contains one sheet named `flashcards`.
