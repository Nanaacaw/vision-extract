"""API routes for OCR functionality."""

import base64
import logging
import time

import fitz
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ocr_engine.ocr import ocr_engine
from ocr_engine.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_IMAGES = {"png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"}
ALLOWED_PDF = {"pdf"}


def validate_file(filename: str) -> str:
    """Validate file extension and return type."""
    if not filename or "." not in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    ext = filename.rsplit(".", 1)[1].lower()

    if ext in ALLOWED_IMAGES:
        return "image"

    if ext in ALLOWED_PDF:
        return "pdf"

    allowed = ", ".join(sorted(ALLOWED_IMAGES | ALLOWED_PDF))
    raise HTTPException(status_code=400, detail=f"Invalid file format. Allowed: {allowed}")


@router.post("/api/ocr/finance")
async def extract_finance_document(
    file: UploadFile = File(...),
    preprocess: bool = Form(settings.preprocess_enabled),
):
    """Extract finance document."""
    file_type = validate_file(file.filename)
    start_time = time.time()

    try:
        is_pdf = file_type == "pdf"
        logger.info("Processing %s (%s)...", file.filename, file_type)
        content = await file.read()
        logger.info("File size: %.1f KB", len(content) / 1024)

        doc = ocr_engine.extract_document(content, preprocess=preprocess, is_pdf=is_pdf)

        elapsed = time.time() - start_time
        logger.info("Processing completed in %.2fs - Type: %s", elapsed, doc.doc_type)

        return JSONResponse(content={
            "success": True,
            "doc_type": doc.doc_type,
            "classification_confidence": doc.classification_confidence,
            "page_count": doc.page_count,
            "json": doc.render_json(),
            "full_text": doc.render_full_text(),
            "markdown": doc.render_markdown(),
            "fields": [
                {"name": field.name, "value": field.value, "confidence": field.confidence}
                for field in doc.fields
            ],
            "review_items": doc.render_review_items(),
            "words": doc.render_words(),
            "blocks": [
                {
                    "text": block.text,
                    "raw_text": block.raw_text,
                    "words": block.words,
                    "type": block.block_type,
                    "bbox": block.bbox,
                    "confidence": block.confidence,
                    "page": block.page,
                }
                for block in doc.blocks
            ],
            "processing_time": round(elapsed, 2),
            "filename": file.filename,
        })

    except Exception as exc:
        elapsed = time.time() - start_time
        logger.error("Extraction error after %.2fs: %s", elapsed, str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Extraction error: {str(exc)}") from exc


@router.post("/api/preview")
async def preview_file(file: UploadFile = File(...)):
    """Generate preview image from uploaded file."""
    try:
        content = await file.read()
        filename = file.filename.lower()

        if filename.endswith(".pdf"):
            pdf_doc = fitz.open(stream=content, filetype="pdf")
            page_count = len(pdf_doc)

            if page_count == 0:
                raise HTTPException(status_code=400, detail="PDF has no pages")

            page = pdf_doc[0]
            mat = fitz.Matrix(settings.pdf_dpi / 72, settings.pdf_dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img_base64 = base64.b64encode(img_data).decode("utf-8")
            pdf_doc.close()

            return JSONResponse(content={
                "success": True,
                "type": "pdf",
                "page_count": page_count,
                "preview": f"data:image/png;base64,{img_base64}",
            })

        image_exts = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp")
        if filename.endswith(image_exts):
            img_base64 = base64.b64encode(content).decode("utf-8")
            return JSONResponse(content={
                "success": True,
                "type": "image",
                "preview": f"data:{file.content_type};base64,{img_base64}",
            })

        raise HTTPException(status_code=400, detail="Unsupported file type")

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Preview error: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preview error: {str(exc)}") from exc


@router.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "OCR AI - Finance Edition",
        "engine": "PaddleOCR PP-OCRv5",
        "ocr_device": settings.ocr_device,
        "ocr_detection_model": settings.ocr_detection_model,
        "ocr_recognition_model": settings.ocr_recognition_model,
        "ocr_textline_orientation": settings.ocr_textline_orientation,
        "ocr_doc_orientation_classify": settings.ocr_doc_orientation_classify,
        "ocr_doc_unwarping": settings.ocr_doc_unwarping,
        "ocr_return_word_box": settings.ocr_return_word_box,
        "pdf_dpi": settings.pdf_dpi,
        "preprocess_enabled": settings.preprocess_enabled,
        "finance_extraction_enabled": settings.finance_extraction_enabled,
        "features": [
            "Canonical document representation",
            "Multi-format rendering (JSON, Markdown, Full Text)",
            "Finance document auto-detection",
            "PDF support",
            "Bounding box coordinates",
        ],
        "supported_documents": [
            "invoice",
            "receipt",
            "payment_slip",
            "tax_invoice",
            "reimbursement",
        ],
    }
