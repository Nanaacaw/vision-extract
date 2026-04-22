# OCR AI - Finance Backend

FastAPI + Next.js service for finance document OCR using PaddleOCR PP-OCRv5 mobile models.

The project accepts invoices, receipts, payment slips, tax invoices, reimbursements, and similar finance documents. It returns a canonical document representation that can be rendered as structured JSON, full text, or markdown.

## Architecture

```text
Upload image/PDF
    -> Next.js review UI
    -> FastAPI route
    -> PaddleOCR engine (PP-OCRv5_mobile_det + PP-OCRv5_mobile_rec)
    -> Canonical Document
    -> JSON / Markdown / Full Text renderers
```

## Quick Start

```bash
pip install -r requirements.txt
npm install --prefix frontend
python main.py
```

Default URLs:

```text
Backend:  http://localhost:8001
Frontend: http://localhost:3001
```

API docs:

```text
http://localhost:8001/docs
```

## Commands

```bash
make install   # Install Python dependencies
make frontend-install
make backend   # Start FastAPI backend on localhost:8001
make frontend  # Start Next.js frontend on localhost:3001
make dev       # Start backend in a separate terminal window
make check     # Compile-check backend modules
make clean     # Remove runtime logs
```

On Windows without `make`, run:

```bat
scripts\start-backend.bat
scripts\start-frontend.bat
scripts\start-all.bat
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
preprocess_profile: auto | receipt | camera | clean | none
smart_crop: true | false
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
docs/
  architecture.md
  flow-system.md
  ocr-models-and-extractors.md
frontend/
  app/
  components/
  lib/
  types/
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

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Flow System](docs/flow-system.md)
- [OCR Models And Extractors](docs/ocr-models-and-extractors.md)
- [Future Plan](docs/future-plan.md)

## Frontend

The frontend is a simple internal review workspace built with:

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui-style local components

The browser calls Next.js API routes under `frontend/app/api/*`. Those routes proxy OCR requests to the FastAPI backend, so client-side code does not need to know the backend URL.

The upload panel supports file upload, drag-and-drop, and live camera capture. Camera frames are captured locally in the browser as JPEG files and are only sent to the backend after the user clicks `Process OCR`.

The frontend also supports batch upload for multiple documents and an optional smart crop toggle for image uploads. Smart crop runs on the backend, keeps OCR boxes aligned to the original preview, and is best used for camera photos with visible table/background around the receipt.

```bat
cd frontend
set OCR_BACKEND_URL=http://localhost:8001
npm run dev -- --port 3001
```

## Notes

- `OCR_BACKEND_PORT` can override the default port.
- `OCR_FRONTEND_PORT` can override the frontend port used by the Windows scripts. Local `.env` currently uses `3001`.
- `OCR_BACKEND_URL` can override the backend URL used by the Next.js proxy.
- `OCR_DET_MODEL` can override the text detection model. Default is `PP-OCRv5_mobile_det`.
- `OCR_REC_MODEL` can override the text recognition model. Default is `PP-OCRv5_mobile_rec`.
- `OCR_TEXTLINE_ORIENTATION=true` can enable the optional text-line orientation classifier.
- `OCR_DOC_ORIENTATION_CLASSIFY=true` can enable page orientation classification.
- `OCR_DOC_UNWARPING=true` can enable document unwarping.
- `OCR_DEVICE` can override the inference device. Default is `cpu`.
- `OCR_PDF_DPI` can override PDF rasterization DPI. Default is `150`.
- `OCR_PREPROCESS=false` can disable image preprocessing by default.
- `OCR_PREPROCESS_PROFILE` sets the default preprocessing profile: `auto`, `receipt`, `camera`, `clean`, or `none`.
- `OCR_SMART_CROP=true` can enable smart document-region cropping by default. It can still be overridden per request.
- `OCR_FINANCE_EXTRACTION=false` can disable finance classification and field extraction.

```bat
set OCR_BACKEND_PORT=8002
set OCR_FRONTEND_PORT=3001
set OCR_DET_MODEL=PP-OCRv5_mobile_det
set OCR_REC_MODEL=PP-OCRv5_mobile_rec
python main.py
```
