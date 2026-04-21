# OCR AI - Finance Backend

Backend-only FastAPI service for finance document OCR using PaddleOCR.

The project accepts invoices, receipts, payment slips, tax invoices, reimbursements, and similar finance documents. It returns a canonical document representation that can be rendered as structured JSON, full text, or markdown.

## Architecture

```text
Upload image/PDF
    -> FastAPI route
    -> PaddleOCR engine
    -> Canonical Document
    -> JSON / Markdown / Full Text renderers
```

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Default backend URL:

```text
http://localhost:8001
```

API docs:

```text
http://localhost:8001/docs
```

## Commands

```bash
make install   # Install Python dependencies
make backend   # Start FastAPI backend on localhost:8001
make dev       # Start backend in a separate terminal window
make check     # Compile-check backend modules
make clean     # Remove runtime logs
```

On Windows without `make`, run:

```bat
scripts\start-backend.bat
```

## API

### Health

```http
GET /api/health
```

### Finance OCR

```http
POST /api/ocr/finance
Content-Type: multipart/form-data
```

Form fields:

```text
file: image or PDF document
preprocess: true | false
```

Example response shape:

```json
{
  "success": true,
  "doc_type": "receipt",
  "classification_confidence": 92,
  "json": {},
  "full_text": "...",
  "markdown": "...",
  "fields": [],
  "blocks": []
}
```

### Preview

```http
POST /api/preview
Content-Type: multipart/form-data
```

Generates a first-page preview for PDFs or image preview payload for images.

## Project Structure

```text
api/
  routes.py
ocr_engine/
  document.py
  ocr.py
  document_classifier.py
  extractors/
  validators/
main.py
requirements.txt
setup.bat
```

## Notes

- This repository is backend-only.
- There is no bundled browser UI.
- `OCR_BACKEND_PORT` can override the default port.

```bat
set OCR_BACKEND_PORT=8002
python main.py
```
