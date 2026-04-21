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
| `OCR_DEVICE` | `cpu` |
| `OCR_PDF_DPI` | `150` |
| `OCR_PREPROCESS` | `true` |
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
    device="cpu",
)
```

OCR execution uses `predict(input=image_np)`. The result is normalized from `rec_texts`, `rec_scores`, and OCR box fields into this project's canonical `Document` blocks.

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
