"""
API routes for OCR functionality with PDF and smart data extraction support.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import time

from ocr_engine.ocr import ocr_engine

router = APIRouter()
logger = logging.getLogger(__name__)

# Allowed file formats
ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif', 'webp'}
ALLOWED_PDF = {'pdf'}


def validate_file(filename: str) -> str:
    """
    Validate file extension and return type.
    
    Returns:
        'image', 'pdf', or raises HTTPException
    """
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


@router.post("/api/ocr")
async def extract_text(
    file: UploadFile = File(...),
    preprocess: bool = Form(True),
    smart_extraction: bool = Form(True)
):
    """
    Extract text from an uploaded image or PDF.

    - **file**: Image or PDF file to process
    - **preprocess**: Apply image preprocessing (default: True)
    - **smart_extraction**: Enable smart data filtering (default: True)
    """
    file_type = validate_file(file.filename)
    
    try:
        content = await file.read()
        
        if file_type == 'pdf':
            result = ocr_engine.extract_from_pdf(content, preprocess=preprocess)
        else:
            result = ocr_engine.extract_text_detailed(content, preprocess=preprocess)

        return JSONResponse(content={
            'success': True,
            'text': result['text'],
            'confidence': result['confidence'],
            'filename': file.filename,
            'type': file_type,
            'smart_data': result.get('structured_data') if smart_extraction else None
        })
    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")


@router.post("/api/ocr/json")
async def extract_text_detailed(
    file: UploadFile = File(...),
    preprocess: bool = Form(True),
    smart_extraction: bool = Form(True),
    include_regions: bool = Form(True)
):
    """
    Extract text with detailed information including regions and smart data.

    Returns text, confidence scores, regions, and structured data.
    """
    file_type = validate_file(file.filename)
    
    try:
        content = await file.read()
        
        if file_type == 'pdf':
            result = ocr_engine.extract_from_pdf(content, preprocess=preprocess)
        else:
            result = ocr_engine.extract_text_detailed(content, preprocess=preprocess)

        response_data = {
            'success': True,
            'data': {
                'text': result['text'],
                'confidence': result['confidence'],
                'word_count': result.get('word_count', 0),
                'type': result.get('type', file_type)
            },
            'filename': file.filename
        }

        # Add regions if requested (for images)
        if include_regions and file_type == 'image':
            response_data['data']['regions'] = result.get('regions', [])
        
        # Add PDF pages detail
        if file_type == 'pdf':
            response_data['data']['page_count'] = result.get('page_count', 0)
            response_data['data']['pages_summary'] = [
                {
                    'page': idx + 1,
                    'text_length': len(page['text']),
                    'confidence': page['confidence']
                }
                for idx, page in enumerate(result.get('pages', []))
            ]

        # Add smart extraction data
        if smart_extraction and result.get('structured_data'):
            response_data['data']['structured_data'] = result['structured_data']

        return JSONResponse(content=response_data)
    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")


@router.post("/api/ocr/extract-data")
async def extract_structured_data(
    file: UploadFile = File(...),
    preprocess: bool = Form(True)
):
    """
    Extract only structured/smart data from document.
    Returns filtered important information (emails, phones, dates, etc.)
    """
    file_type = validate_file(file.filename)
    
    try:
        content = await file.read()
        
        if file_type == 'pdf':
            result = ocr_engine.extract_from_pdf(content, preprocess=preprocess)
        else:
            result = ocr_engine.extract_text_detailed(content, preprocess=preprocess)

        return JSONResponse(content={
            'success': True,
            'filename': file.filename,
            'structured_data': result.get('structured_data', {}),
            'summary': {
                'emails_found': len(result.get('structured_data', {}).get('emails', [])),
                'phones_found': len(result.get('structured_data', {}).get('phones', [])),
                'dates_found': len(result.get('structured_data', {}).get('dates', [])),
                'prices_found': len(result.get('structured_data', {}).get('prices', [])),
            }
        })
    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")


@router.post("/api/preview")
async def preview_file(file: UploadFile = File(...)):
    """
    Generate preview image from uploaded file.
    For PDFs: converts first page to image.
    For images: returns base64 directly.
    """
    import fitz
    import base64

    try:
        content = await file.read()
        filename = file.filename.lower()

        if filename.endswith('.pdf'):
            # Convert PDF first page to image
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
            'PDF support', 
            'Smart extraction', 
            'Logo detection',
            'Finance document auto-detection',
            'Invoice extraction',
            'Receipt extraction',
            'Payment slip extraction',
            'Tax invoice (Faktur) extraction',
            'Reimbursement extraction'
        ],
        'supported_documents': [
            'invoice',
            'receipt',
            'payment_slip',
            'tax_invoice',
            'reimbursement'
        ]
    }


@router.post("/api/ocr/finance")
async def extract_finance_document(
    file: UploadFile = File(...),
    preprocess: bool = Form(True)
):
    """
    Auto-detect and extract finance document.
    Automatically classifies document type and extracts relevant data.
    """
    file_type = validate_file(file.filename)
    start_time = time.time()
    
    try:
        is_pdf = file_type == 'pdf'
        logger.info(f"📄 Processing {file.filename} ({file_type})...")
        content = await file.read()
        logger.info(f"📊 File size: {len(content) / 1024:.1f} KB")
        
        # Finance extraction with auto-detection
        result = ocr_engine.extract_finance_document(
            content, 
            preprocess=preprocess,
            is_pdf=is_pdf
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Processing completed in {elapsed:.2f}s - Type: {result.get('doc_type', 'unknown')}")
        
        return JSONResponse(content={
            'success': result['success'],
            'doc_type': result.get('doc_type', 'unknown'),
            'classification_confidence': result.get('classification_confidence', 0),
            'extraction_confidence': result.get('extraction_confidence', 0),
            'data': {
                **result.get('data', {}),
                'full_text': result.get('full_text', ''),
                'words': result.get('words', []),
                # Include image dimensions for proper scaling
                'ocr_width': result.get('width', 0),
                'ocr_height': result.get('height', 0)
            },
            'validation_errors': result.get('validation_errors', {}),
            'warnings': result.get('warnings', []),
            'classification_reasons': result.get('classification_reasons', []),
            'processing_time': round(elapsed, 2),
            'filename': file.filename
        })
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ Finance extraction error after {elapsed:.2f}s: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Finance extraction error: {str(e)}")
