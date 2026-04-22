# OCR Models And Extractors

## OCR Model

The OCR path is intentionally simple: this project uses PaddleOCR PP-OCRv5 mobile models directly.

| Setting | Default |
| --- | --- |
| `OCR_DET_MODEL` | `PP-OCRv5_mobile_det` |
| `OCR_REC_MODEL` | `PP-OCRv5_mobile_rec` |
| `OCR_TEXTLINE_ORIENTATION` | `false` |
| `OCR_DOC_ORIENTATION_CLASSIFY` | `false` |
| `OCR_DOC_UNWARPING` | `false` |
| `OCR_RETURN_WORD_BOX` | `true` |
| `OCR_DEVICE` | `cpu` |
| `OCR_PDF_DPI` | `150` |
| `OCR_PREPROCESS` | `true` |
| `OCR_PREPROCESS_PROFILE` | `auto` |
| `OCR_FINANCE_EXTRACTION` | `true` |

All runtime settings are centralized in `ocr_engine/settings.py`.

The engine initializes PaddleOCR like this:

```python
PaddleOCR(
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    return_word_box=True,
    device="cpu",
)
```

OCR execution uses `predict(input=image_np)`. The result is normalized from `rec_texts`, `rec_scores`, and OCR box fields into this project's canonical `Document` blocks.

## Camera Capture

The frontend can capture documents directly from the browser camera. The captured frame is converted to a local JPEG `File`, then sent through the same upload path as normal images.

Important constraints:

- camera access works on `localhost` or HTTPS, not arbitrary insecure HTTP origins
- capture quality depends heavily on focus, lighting, distance, and paper angle
- the backend still receives a normal image upload, so no special camera endpoint is required
- users should review block and word confidence after capture because camera photos are usually less stable than scanned files

## Word-Level Accuracy Tuning

For better extraction of every word, tune the pipeline in this order:

1. Improve capture quality before changing models:
   - use rear camera where available
   - keep the receipt flat and fully inside frame
   - avoid shadows, glare, blur, and strong perspective
   - capture at high resolution, then let preprocessing simplify the image
2. Keep `OCR_RETURN_WORD_BOX=true` so PaddleOCR returns native word boxes when available.
3. Evaluate preprocessing variants per sample set:
   - current denoise + adaptive threshold
   - grayscale only for clean printed invoices
   - contrast/sharpen for faded thermal receipts
   - no thresholding for screenshots or already-clean scans
4. Enable optional orientation/unwarping only if the dataset needs it:
   - `OCR_TEXTLINE_ORIENTATION=true` for rotated text lines
   - `OCR_DOC_ORIENTATION_CLASSIFY=true` for sideways pages
   - `OCR_DOC_UNWARPING=true` for curved/warped camera photos
5. Raise PDF rasterization when PDFs are blurry:
   - try `OCR_PDF_DPI=200` or `OCR_PDF_DPI=300`
   - expect slower processing and higher memory use
6. Compare recognition models on the same Indonesian finance sample set:
   - current `PP-OCRv5_mobile_rec`
   - `latin_PP-OCRv5_mobile_rec` for Latin-script-heavy Indonesian documents
7. Add post-OCR correction rules for finance text:
   - `O` vs `0`
   - `I/l` vs `1`
   - common bank/account/reference labels
   - Indonesian amount and date formats

The biggest practical gain will usually come from capture quality, preprocessing profiles, and layout-aware extraction using bounding boxes. Changing the model should come after measuring field-level accuracy on real invoices, receipts, payment slips, and tax documents.

The backend also runs a layout-aware fallback for `receipt` and `payment_slip` documents. It uses OCR block positions to recover missing values such as totals, dates, transaction IDs, payment amounts, and currencies when regex extraction over full text misses them. The API exposes recovered values in `layout_evidence` and any remaining required gaps in `missing_fields`.

## Preprocessing Profiles

Preprocessing is configured globally with `OCR_PREPROCESS_PROFILE`, but each OCR request can override it with `preprocess_profile`.

| Profile | Use case | Behavior |
| --- | --- | --- |
| `auto` | Default | Uses `clean` for PDFs and `receipt` for images. |
| `clean` | Clean PDF or scanned invoice | Light contrast normalization without thresholding. |
| `receipt` | Printed or thermal receipt | Denoise, local contrast enhancement, and mild sharpening. |
| `camera` | Camera capture | Stronger contrast, denoise, sharpening, and adaptive thresholding. |
| `none` | Screenshot or already-clean image | Sends the decoded image directly to PaddleOCR. |

All profiles preserve image dimensions so OCR bounding boxes remain aligned with the frontend document preview.

## Indonesian Finance Documents

PP-OCRv5 is a reasonable local OCR baseline for Indonesian finance documents because Indonesian uses Latin script and finance documents are usually rich in structured printed text, numbers, dates, totals, bank references, and tax IDs.

What helps:

- OCR runs locally, so sensitive finance files are not sent to a third-party OCR service by default.
- Mobile models are compact and suitable for CPU-first development.
- OCR output includes boxes and confidence, which fits human review workflows.
- Rule-based finance extraction remains deterministic and auditable.

What can hurt accuracy:

- low-light camera photos
- skewed or curved receipts
- thermal receipt noise
- aggressive thresholding that removes thin text
- mixed Indonesian/English labels
- table layouts where OCR text order differs from visual order

If Indonesian accuracy is not good enough during evaluation, test `OCR_REC_MODEL=latin_PP-OCRv5_mobile_rec` on the same sample set and compare field-level accuracy.

## Extractor Architecture Assessment

The extractor concept remains good as a first production baseline:

- one classifier
- one extractor per document type
- shared `BaseExtractor`
- validation separated into `FinanceValidator`
- canonical `Document` object before rendering

This is efficient because common documents do not need an expensive model call. It is also easier to debug than an LLM-only pipeline.

## Current Weaknesses

The current extractors are mostly regex over full text. That means they can struggle when:

- OCR output order is different from visual order
- labels and values are split across lines
- Indonesian labels vary by vendor or bank
- amount formats use dots as thousand separators
- field confidence is calculated by filled-field ratio instead of field-level evidence
- spatial coordinates are ignored even though OCR blocks include bounding boxes

## Recommended Improvement Path

1. Keep rule-based classifier and extractors as the primary path.
2. Add better Indonesian aliases for labels:
   - `tanggal`, `nomor`, `jumlah`, `nominal`, `penerima`, `pengirim`, `rekening`, `npwp`, `dpp`, `ppn`
3. Normalize Indonesian money formats:
   - `Rp 1.234.567`
   - `1.234.567,00`
   - `IDR 1,234,567`
4. Use OCR block coordinates for key-value proximity.
5. Add sample-based tests per document type.
6. Add optional LLM review only for:
   - `doc_type == unknown`
   - low classification confidence
   - missing required fields
   - validation failures

## Should We Use A Free LLM For Classification?

Not as the default path.

Reasons:

- finance documents are sensitive
- free hosted LLMs often have unclear retention and privacy guarantees
- network calls add latency and failure modes
- deterministic rules are enough for common known categories
- LLM output still needs validation

Good use of an LLM:

```text
OCR text
  -> rule classifier
  -> if high confidence: extractor
  -> if low confidence: local/manual review or optional LLM review
  -> schema validation
  -> never trust LLM output without validator
```

If using an LLM, prefer a local model or a provider with strong data-processing guarantees. Send redacted OCR text where possible, not raw images.

## Recommended Next Code Refactor

The next useful refactor is adding a shared parser utility layer:

```text
ocr_engine/
  parsers/
    money.py
    dates.py
    ids.py
    key_value.py
```

This reduces duplicated regex logic across extractors and makes test coverage easier.

## References

- PaddleOCR General OCR pipeline usage tutorial: https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html
- PaddleOCR PP-OCRv5 introduction: https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html
