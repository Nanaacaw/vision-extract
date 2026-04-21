# Architecture

This project is a backend-only Finance OCR service. It receives image or PDF documents, runs PaddleOCR, builds a canonical `Document`, classifies the document type, runs a finance-specific extractor, and returns API-friendly renderings.

## Runtime Stack

| Layer | Technology | Responsibility |
| --- | --- | --- |
| API | FastAPI | Upload endpoints, preview endpoint, health endpoint |
| OCR | PaddleOCR PP-OCRv5 | Text detection and recognition |
| PDF rasterization | PyMuPDF | Convert PDF pages into images before OCR |
| Image processing | OpenCV + Pillow | Decode, normalize, denoise, threshold |
| Domain model | `ocr_engine.document.Document` | Canonical blocks, fields, metadata, renderers |
| Classification | `ocr_engine.document_classifier.DocumentClassifier` | Rule-based document type classification |
| Extraction | `ocr_engine.extractors.*` | Document-type-specific field extraction |
| Validation | `ocr_engine.validators.finance.FinanceValidator` | Consistency checks for amounts, dates, NPWP, accounts |

## Request Architecture

```text
Client
  -> POST /api/ocr/finance
  -> validate_file()
  -> read UploadFile bytes
  -> OCREngine.extract_document()
      -> image path or PDF path
      -> PaddleOCR PP-OCRv5 `predict()`
      -> Document.add_blocks_from_ocr()
      -> DocumentClassifier.classify()
      -> matching extractor.extract()
      -> FinanceValidator checks
  -> JSONResponse
```

## Main Modules

```text
api/
  routes.py                 API routes and diagnostics

ocr_engine/
  ocr.py                    OCR orchestration and PDF/image processing
  document.py               Canonical document object and renderers
  document_classifier.py    Rule-based finance document classifier
  extractors/
    base.py                 Extractor interface and helpers
    invoice.py
    receipt.py
    payment_slip.py
    tax_invoice.py
    reimbursement.py
  validators/
    finance.py              Domain validation helpers
```

## Configuration

Runtime settings live in `ocr_engine/settings.py`. The backend loads `.env` first, then reads environment variables, so local configuration can stay outside Git.

```text
OCR_DET_MODEL=PP-OCRv5_mobile_det
OCR_REC_MODEL=PP-OCRv5_mobile_rec
OCR_TEXTLINE_ORIENTATION=false
OCR_DOC_ORIENTATION_CLASSIFY=false
OCR_DOC_UNWARPING=false
OCR_RETURN_WORD_BOX=true
OCR_DEVICE=cpu
OCR_PDF_DPI=150
OCR_PREPROCESS=true
OCR_FINANCE_EXTRACTION=true
OCR_BACKEND_PORT=8001
```

PaddleOCR downloads the configured PP-OCRv5 models on first use if they are not already cached.

## API Surface

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Backend metadata |
| `GET /api/health` | Health, model names, device, and processing settings |
| `POST /api/ocr/finance` | Extract OCR text and structured finance fields |
| `POST /api/preview` | Generate a preview payload for image/PDF clients |

## Current Design Tradeoffs

- Rule-based classification is fast, cheap, deterministic, and private.
- Extractors are simple and easy to debug, but brittle against unusual layouts, OCR errors, and mixed wording.
- The current service does not require an LLM to classify common finance documents.
- An LLM can be added later for low-confidence or unknown documents.
