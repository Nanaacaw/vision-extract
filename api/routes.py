"""
API routes for OCR functionality.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from ocr_engine.ocr import ocr_engine

router = APIRouter()
logger = logging.getLogger(__name__)

# Allowed image formats
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif', 'webp'}


def validate_image(filename: str) -> bool:
    """Validate image file extension."""
    if not filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@router.post("/api/ocr")
async def extract_text(file: UploadFile = File(...), preprocess: bool = Form(True)):
    """
    Extract text from an uploaded image.
    
    - **file**: Image file to process
    - **preprocess**: Apply image preprocessing (default: True)
    """
    if not validate_image(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        content = await file.read()
        text = ocr_engine.extract_text(content, preprocess=preprocess)
        
        return JSONResponse(content={
            'success': True,
            'text': text,
            'filename': file.filename
        })
    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")


@router.post("/api/ocr/json")
async def extract_text_detailed(file: UploadFile = File(...), preprocess: bool = Form(True)):
    """
    Extract text from an uploaded image with detailed information.
    
    Returns text, confidence scores, and word-level data.
    """
    if not validate_image(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        content = await file.read()
        result = ocr_engine.extract_text_detailed(content, preprocess=preprocess)
        
        return JSONResponse(content={
            'success': True,
            'data': result,
            'filename': file.filename
        })
    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")


@router.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'service': 'OCR AI'
    }
