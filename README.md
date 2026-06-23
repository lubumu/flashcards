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

## Flashcard Apps

The project now includes two study applications that both use the same SQLite progress database.

### Desktop app

```bash
python flashcard_app.py
```

### Web app

Install dependencies first:

```bash
pip install -r requirements.txt
```

Then start the Flask server:

```bash
python flashcard_web.py
```

Open `http://127.0.0.1:5000` in your browser.

The web app keeps progress in `flashcards.db`, grouped by lesson, and uses the same adaptive repetition weights as the desktop app.
