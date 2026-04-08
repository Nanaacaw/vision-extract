"""
API routes for OCR functionality.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
import logging
import time

from ocr_engine.ocr import ocr_engine

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif', 'webp'}
ALLOWED_PDF = {'pdf'}


def validate_file(filename: str) -> str:
    """Validate file extension and return type."""
    if not filename or '.' not in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    if ext in ALLOWED_IMAGES:
        return 'image'
    elif ext in ALLOWED_PDF:
        return 'pdf'
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed: {', '.join(ALLOWED_IMAGES)}, {', '.join(ALLOWED_PDF)}"
        )


@router.post("/api/ocr/finance")
async def extract_finance_document(
    file: UploadFile = File(...),
    preprocess: bool = Form(True)
):
    """Extract finance document."""
    file_type = validate_file(file.filename)
    start_time = time.time()
    
    try:
        is_pdf = file_type == 'pdf'
        logger.info(f"📄 Processing {file.filename} ({file_type})...")
        content = await file.read()
        logger.info(f"📊 File size: {len(content) / 1024:.1f} KB")
        
        # Extract canonical document
        doc = ocr_engine.extract_document(content, preprocess=preprocess, is_pdf=is_pdf)
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Processing completed in {elapsed:.2f}s - Type: {doc.doc_type}")
        
        return JSONResponse(content={
            'success': True,
            'doc_type': doc.doc_type,
            'classification_confidence': doc.classification_confidence,
            'page_count': doc.page_count,
            'json': doc.render_json(),
            'full_text': doc.render_full_text(),
            'markdown': doc.render_markdown(),
            'fields': [{'name': f.name, 'value': f.value, 'confidence': f.confidence} for f in doc.fields],
            'blocks': [
                {'text': b.text, 'type': b.block_type, 'bbox': b.bbox, 'confidence': b.confidence, 'page': b.page}
                for b in doc.blocks
            ],
            'processing_time': round(elapsed, 2),
            'filename': file.filename
        })
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ Extraction error after {elapsed:.2f}s: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Extraction error: {str(e)}")


@router.post("/api/preview")
async def preview_file(file: UploadFile = File(...)):
    """Generate preview image from uploaded file."""
    import fitz
    import base64

    try:
        content = await file.read()
        filename = file.filename.lower()

        if filename.endswith('.pdf'):
            pdf_doc = fitz.open(stream=content, filetype="pdf")
            page_count = len(pdf_doc)
            
            if page_count > 0:
                page = pdf_doc[0]
                mat = fitz.Matrix(150 / 72, 150 / 72)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                img_base64 = base64.b64encode(img_data).decode('utf-8')
            else:
                raise HTTPException(status_code=400, detail="PDF has no pages")
            
            pdf_doc.close()

            return JSONResponse(content={
                'success': True,
                'type': 'pdf',
                'page_count': page_count,
                'preview': f'data:image/png;base64,{img_base64}'
            })

        elif any(filename.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp']):
            img_base64 = base64.b64encode(content).decode('utf-8')
            return JSONResponse(content={
                'success': True,
                'type': 'image',
                'preview': f'data:{file.content_type};base64,{img_base64}'
            })

        raise HTTPException(status_code=400, detail="Unsupported file type")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preview error: {str(e)}")


@router.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'service': 'OCR AI - Finance Edition',
        'engine': 'PaddleOCR',
        'features': [
            'Canonical document representation',
            'Multi-format rendering (JSON, Markdown, Full Text)',
            'Finance document auto-detection',
            'PDF support',
            'Bounding box visualization'
        ],
        'supported_documents': ['invoice', 'receipt', 'payment_slip', 'tax_invoice', 'reimbursement']
    }
