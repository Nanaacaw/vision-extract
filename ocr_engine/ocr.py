"""
Core OCR engine using Tesseract.
"""

import pytesseract
from PIL import Image
import io
from typing import Optional

from .preprocessing import preprocess_image


class OCREngine:
    """OCR engine for extracting text from images."""

    def __init__(self, tesseract_cmd: Optional[str] = None, language: str = 'eng'):
        """
        Initialize OCR engine.
        
        Args:
            tesseract_cmd: Path to tesseract executable (optional)
            language: Language code for OCR (default: 'eng')
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        self.language = language
        self.config = r'--oem 3 --psm 6'  # OEM 3: Default, PSM 6: Uniform block of text

    def extract_text(self, image_data: bytes, preprocess: bool = True) -> str:
        """
        Extract text from image bytes.
        
        Args:
            image_data: Image bytes
            preprocess: Whether to apply image preprocessing
            
        Returns:
            Extracted text string
        """
        image = Image.open(io.BytesIO(image_data))
        
        if preprocess:
            image = preprocess_image(image)
        
        text = pytesseract.image_to_string(
            image,
            lang=self.language,
            config=self.config
        )
        
        return text.strip()

    def extract_text_detailed(self, image_data: bytes, preprocess: bool = True) -> dict:
        """
        Extract text with detailed information.
        
        Args:
            image_data: Image bytes
            preprocess: Whether to apply image preprocessing
            
        Returns:
            Dictionary with text, confidence, and word-level details
        """
        image = Image.open(io.BytesIO(image_data))
        
        if preprocess:
            image = preprocess_image(image)
        
        # Get full text
        text = pytesseract.image_to_string(
            image,
            lang=self.language,
            config=self.config
        ).strip()
        
        # Get detailed data
        data = pytesseract.image_to_data(
            image,
            lang=self.language,
            config=self.config,
            output_type=pytesseract.Output.DICT
        )
        
        # Extract word-level information
        words = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            if int(data['conf'][i]) > 0:
                words.append({
                    'text': data['text'][i],
                    'confidence': int(data['conf'][i]),
                    'left': data['left'][i],
                    'top': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'line_num': data['line_num'][i],
                    'block_num': data['block_num'][i]
                })

        avg_confidence = sum(w['confidence'] for w in words) / len(words) if words else 0
        
        return {
            'text': text,
            'confidence': round(avg_confidence, 2),
            'word_count': len(words),
            'words': words
        }

    def set_language(self, language: str):
        """Set OCR language."""
        self.language = language

    def get_supported_languages(self) -> list:
        """Get list of supported languages (common ones)."""
        return [
            'eng', 'chi_sim', 'chi_tra', 'fra', 'deu', 'spa', 
            'jpn', 'kor', 'rus', 'ara', 'hin', 'ita', 'por'
        ]


# Default instance
ocr_engine = OCREngine()
