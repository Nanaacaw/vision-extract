# API Reference

Base URL:

```text
http://localhost:8001
```

## Health

```http
GET /api/health
```

Returns service status and active OCR configuration.

Example response:

```json
{
  "status": "healthy",
  "service": "OCR AI - Finance Edition",
  "engine": "PaddleOCR PP-OCRv5",
  "ocr_device": "cpu",
  "ocr_detection_model": "PP-OCRv5_mobile_det",
  "ocr_recognition_model": "PP-OCRv5_mobile_rec",
  "ocr_textline_orientation": false,
  "ocr_doc_orientation_classify": false,
  "ocr_doc_unwarping": false,
  "ocr_return_word_box": true,
  "pdf_dpi": 150,
  "preprocess_enabled": true,
  "finance_extraction_enabled": true
}
```

## Finance OCR

```http
POST /api/ocr/finance
Content-Type: multipart/form-data
```

Form fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `file` | file | yes | Image or PDF document. Supported: `png`, `jpg`, `jpeg`, `bmp`, `tiff`, `tif`, `webp`, `pdf`. |
| `preprocess` | boolean | no | Overrides default image preprocessing for this request. |

Example curl:

```bash
curl -X POST http://localhost:8001/api/ocr/finance \
  -F "file=@input/2.png" \
  -F "preprocess=true"
```

Response fields:

| Field | Type | Description |
| --- | --- | --- |
| `success` | boolean | Processing result flag. |
| `doc_type` | string | Classified finance document type. |
| `classification_confidence` | number | Classifier confidence score. |
| `page_count` | number | Number of processed pages. |
| `json` | object | Canonical document rendering. |
| `full_text` | string | Cleaned OCR text suitable for reading/extraction. |
| `markdown` | string | Markdown rendering of the canonical document. |
| `fields` | array | Structured finance fields from extractors. |
| `blocks` | array | Cleaned OCR text blocks with bounding boxes and nested word review items. |
| `review_items` | array | Block-level review model for UI review/correction workflows. |
| `words` | array | Flat word-level review list derived from cleaned OCR blocks and PaddleOCR word boxes. |
| `processing_time` | number | Processing time in seconds. |
| `filename` | string | Original uploaded filename. |

Block shape:

```json
{
  "text": "Total Payment",
  "raw_text": null,
  "type": "heading",
  "bbox": { "x": 287, "y": 540, "width": 176, "height": 27 },
  "confidence": 0.98,
  "page": 1,
  "words": [
    {
      "text": "Total",
      "bbox": { "x": 287, "y": 540, "width": 73, "height": 27 },
      "confidence": 0.98,
      "page": 1,
      "index": 0
    }
  ]
}
```

Review item shape:

```json
{
  "id": "p1-b5",
  "level": "block",
  "text": "Total Payment",
  "raw_text": null,
  "type": "heading",
  "bbox": { "x": 287, "y": 540, "width": 176, "height": 27 },
  "confidence": 0.98,
  "page": 1,
  "status": "ready",
  "words": [
    {
      "id": "p1-b5-w1",
      "level": "word",
      "text": "Total",
      "source": "paddle_word_box",
      "bbox": { "x": 287, "y": 540, "width": 73, "height": 27 },
      "confidence": 0.98,
      "page": 1,
      "index": 0,
      "status": "ready"
    }
  ]
}
```

Text cleanup behavior:

- Removes OCR artifacts that are only decorative separators, such as `==========`, `||||`, and `-----`.
- Removes visual/parser labels such as `DANA logo`, `Image: Success icon`, `PICTURE`, `TEXT`, and `SECTIONHEADER`.
- Collapses excessive spaces and line breaks inside a detected OCR block.
- Preserves masked finance values such as `Marchel An****n`, account fragments, and transaction IDs.
- Keeps `raw_text` when cleaned text differs from OCR output, so the UI can show what changed.
- Uses PaddleOCR word boxes when `OCR_RETURN_WORD_BOX=true`; otherwise word boxes are estimated from the parent block box.

## Preview

```http
POST /api/preview
Content-Type: multipart/form-data
```

Form fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `file` | file | yes | Image or PDF document. |

Returns a base64 preview. PDFs return the first page rasterized using `OCR_PDF_DPI`.

Example response:

```json
{
  "success": true,
  "type": "pdf",
  "page_count": 1,
  "preview": "data:image/png;base64,..."
}
```

## Error Responses

Invalid upload:

```json
{
  "detail": "Invalid file format. Allowed: bmp, jpeg, jpg, pdf, png, tif, tiff, webp"
}
```

Processing failure:

```json
{
  "detail": "Extraction error: <message>"
}
```
