"""
Core OCR engine using PaddleOCR with PDF support and smart data extraction.
"""

import cv2
import numpy as np
from PIL import Image
import io
import fitz  # PyMuPDF
from typing import Optional, List, Dict, Tuple
from paddleocr import PaddleOCR
import logging
import re

from .document_classifier import classifier, ClassificationResult
from .extractors import (
    InvoiceExtractor,
    ReceiptExtractor,
    PaymentSlipExtractor,
    TaxInvoiceExtractor,
    ReimbursementExtractor
)
from .validators.finance import FinanceValidator

logger = logging.getLogger(__name__)


class OCREngine:
    """Advanced OCR engine using PaddleOCR for PDF, images, and smart data extraction."""

    def __init__(
        self,
        language: str = 'en',
        use_angle_cls: bool = True,
        use_gpu: bool = False,
        enable_smart_extraction: bool = True,
        enable_finance_extraction: bool = True
    ):
        """
        Initialize OCR engine.

        Args:
            language: Language code ('en', 'ch', etc.)
            use_angle_cls: Enable text angle classification (for rotated text/logos)
            use_gpu: Use GPU acceleration if available
            enable_smart_extraction: Enable intelligent data filtering
            enable_finance_extraction: Enable finance document auto-detection
        """
        self.language = language
        self.enable_smart_extraction = enable_smart_extraction
        self.enable_finance_extraction = enable_finance_extraction

        # Initialize extractors
        self.invoice_extractor = InvoiceExtractor()
        self.receipt_extractor = ReceiptExtractor()
        self.payment_slip_extractor = PaymentSlipExtractor()
        self.tax_invoice_extractor = TaxInvoiceExtractor()
        self.reimbursement_extractor = ReimbursementExtractor()
        self.validator = FinanceValidator()

        # Initialize PaddleOCR with optimized settings
        self.ocr = PaddleOCR(
            use_angle_cls=use_angle_cls,
            lang=language,
            use_gpu=use_gpu,
            show_log=False,
            rec_model_dir=None,
            det_model_dir=None,
            cls_model_dir=None,
            use_space_char=True,
            drop_score=0.5,  # Skip low confidence detections
            max_text_length=1000  # Limit text length for speed
        )

    def extract_text(self, image_data: bytes, preprocess: bool = True) -> str:
        """
        Extract text from image bytes.

        Args:
            image_data: Image bytes
            preprocess: Whether to apply image preprocessing

        Returns:
            Extracted text string
        """
        result = self.extract_text_detailed_with_words(image_data, preprocess=preprocess)
        return result.get('text', '')

    def extract_text_detailed_with_words(self, image_data: bytes, preprocess: bool = True) -> dict:
        """
        Extract text with word-level position data for interactive highlighting.

        Args:
            image_data: Image bytes
            preprocess: Whether to apply image preprocessing

        Returns:
            Dictionary with text, confidence, and words with bbox
        """
        # Convert bytes to image
        image = Image.open(io.BytesIO(image_data))
        image_np = np.array(image)

        # Convert RGBA to RGB if needed
        if len(image_np.shape) == 3 and image_np.shape[2] == 4:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)

        # Apply preprocessing if requested
        if preprocess:
            image_np = self._preprocess_for_paddle(image_np)

        # Run OCR
        ocr_result = self.ocr.ocr(image_np, cls=True)
        
        # Build words list
        words = []
        all_text = []
        
        if ocr_result and ocr_result[0]:
            for idx, (box, (text, confidence)) in enumerate(ocr_result[0]):
                if text and text.strip():
                    box_coords = np.array(box).astype(int)
                    x_min = int(np.min(box_coords[:, 0]))
                    y_min = int(np.min(box_coords[:, 1]))
                    x_max = int(np.max(box_coords[:, 0]))
                    y_max = int(np.max(box_coords[:, 1]))
                    
                    words.append({
                        'text': text.strip(),
                        'confidence': round(float(confidence), 2),
                        'bbox': {
                            'x': x_min,
                            'y': y_min,
                            'width': x_max - x_min,
                            'height': y_max - y_min
                        }
                    })
                    all_text.append(text.strip())
        
        avg_conf = sum(w['confidence'] for w in words) / len(words) if words else 0

        return {
            'text': '\n'.join(all_text),
            'confidence': round(avg_conf, 2),
            'words': words,
            'width': image.width,
            'height': image.height
        }

    def extract_from_pdf(self, pdf_data: bytes, preprocess: bool = True, dpi: int = 200) -> dict:
        """
        Extract text from PDF file with word-level position data.

        Args:
            pdf_data: PDF file bytes
            preprocess: Apply preprocessing to each page
            dpi: Resolution for PDF to image conversion (default: 200 for speed)

        Returns:
            Dictionary with text, confidence, structured data per page
        """
        try:
            # Open PDF with PyMuPDF
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            num_pages = len(pdf_document)

            all_pages_text = []
            all_pages_confidence = []
            all_pages_data = []
            all_words = []

            for page_num in range(num_pages):
                # Convert page to image
                page = pdf_document[page_num]
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat)

                # Convert to numpy
                img_data = pix.tobytes("png")
                image_np = np.frombuffer(img_data, dtype=np.uint8)
                image_np = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
                
                # Store actual image dimensions
                actual_height, actual_width = image_np.shape[:2]

                # Apply preprocessing
                if preprocess:
                    image_np = self._preprocess_for_paddle(image_np)

                # Run OCR with detailed word-level data
                try:
                    ocr_result = self.ocr.ocr(image_np, cls=True)
                except Exception as e:
                    logger.error(f"OCR error on page {page_num + 1}: {str(e)}")
                    continue
                
                # Build words list
                words = []
                if ocr_result and ocr_result[0]:
                    for idx, (box, (text, confidence)) in enumerate(ocr_result[0]):
                        if text and text.strip():
                            box_coords = np.array(box).astype(int)
                            x_min = int(np.min(box_coords[:, 0]))
                            y_min = int(np.min(box_coords[:, 1]))
                            x_max = int(np.max(box_coords[:, 0]))
                            y_max = int(np.max(box_coords[:, 1]))
                            
                            words.append({
                                'text': text.strip(),
                                'confidence': round(float(confidence), 2),
                                'bbox': {
                                    'x': x_min,
                                    'y': y_min,
                                    'width': x_max - x_min,
                                    'height': y_max - y_min
                                },
                                'page': page_num + 1
                            })

                page_text = ' '.join(w['text'] for w in words)
                avg_conf = sum(w['confidence'] for w in words) / len(words) if words else 0

                all_pages_text.append(page_text)
                all_pages_confidence.append(avg_conf)
                all_words.extend(words)

                all_pages_data.append({
                    'page': page_num + 1,
                    'text': page_text,
                    'confidence': round(avg_conf, 2),
                    'words': words,
                    'width': actual_width,
                    'height': actual_height
                })

            pdf_document.close()

            full_text = '\n\n'.join(all_pages_text)
            overall_conf = sum(all_pages_confidence) / len(all_pages_confidence) if all_pages_confidence else 0

            return {
                'text': full_text,
                'confidence': round(overall_conf, 2),
                'page_count': num_pages,
                'pages': all_pages_data,
                'words': all_words,  # Word-level data for highlighting
                'width': all_pages_data[0]['width'] if all_pages_data else 0,  # First page dimensions
                'height': all_pages_data[0]['height'] if all_pages_data else 0,
                'type': 'pdf'
            }

        except Exception as e:
            logger.error(f"PDF processing error: {str(e)}", exc_info=True)
            raise

    def extract_finance_document(self, file_data: bytes, preprocess: bool = True, is_pdf: bool = False) -> dict:
        """
        Auto-detect and extract finance document with full validation.
        
        Args:
            file_data: File bytes (image or PDF)
            preprocess: Apply preprocessing
            is_pdf: Whether the file is a PDF
            
        Returns:
            Dictionary with finance extraction results
        """
        try:
            # Handle PDF vs Image
            if is_pdf:
                # Extract text from PDF with word-level data
                ocr_result = self.extract_from_pdf(file_data, preprocess=preprocess)
                text = ocr_result['text']
                words = ocr_result.get('words', [])
                width = ocr_result.get('width', 0)
                height = ocr_result.get('height', 0)
            else:
                # Extract text from image with word-level data
                ocr_result = self.extract_text_detailed_with_words(file_data, preprocess=preprocess)
                text = ocr_result['text']
                words = ocr_result.get('words', [])
                width = ocr_result.get('width', 0)
                height = ocr_result.get('height', 0)
            
            if not text or not text.strip():
                return {
                    'success': False,
                    'error': 'No text detected',
                    'doc_type': 'unknown'
                }
            
            # Step 1: Classify document type
            classification = classifier.classify(text)
            
            # Step 2: Use appropriate extractor
            extractor = self._get_extractor(classification.doc_type)
            
            if extractor:
                # Extract finance data
                extraction_result = extractor.extract(text)
                
                # Validate
                validation_errors = self.validator.validate_document(
                    extraction_result.doc_type,
                    extraction_result.data
                )
                
                return {
                    'success': True,
                    'doc_type': classification.doc_type,
                    'classification_confidence': classification.confidence,
                    'extraction_confidence': extraction_result.confidence,
                    'data': {
                        **extraction_result.data,
                    },
                    'full_text': text,
                    'words': words,  # Word-level data for highlighting
                    'width': width,
                    'height': height,
                    'validation_errors': validation_errors,
                    'warnings': extraction_result.warnings,
                    'classification_reasons': classification.reasons
                }
            else:
                # Fallback to generic extraction
                return {
                    'success': True,
                    'doc_type': 'unknown',
                    'classification_confidence': classification.confidence,
                    'full_text': text,
                    'words': words,
                    'width': width,
                    'height': height,
                    'message': 'Generic OCR - not recognized as finance document'
                }
        except Exception as e:
            logger.error(f"extract_finance_document error: {str(e)}", exc_info=True)
            raise
    
    def _get_extractor(self, doc_type: str):
        """Get appropriate extractor for document type."""
        extractors = {
            'invoice': self.invoice_extractor,
            'receipt': self.receipt_extractor,
            'payment_slip': self.payment_slip_extractor,
            'tax_invoice': self.tax_invoice_extractor,
            'reimbursement': self.reimbursement_extractor
        }
        return extractors.get(doc_type)

    def _run_ocr(self, image_np: np.ndarray) -> list:
        """Run PaddleOCR on image and return raw results."""
        try:
            result = self.ocr.ocr(image_np, cls=True)
            
            # Handle different PaddleOCR result formats
            if not result or not result[0]:
                return []
            
            # Result is nested list: [[ [box, (text, confidence)], ... ]]
            return result[0] if result else []
            
        except Exception as e:
            logger.error(f"OCR processing error: {str(e)}")
            return []

    def _structure_results(self, ocr_results: list, image_shape: Tuple) -> dict:
        """Structure OCR results with regions and confidence."""
        if not ocr_results:
            return {
                'text': '',
                'confidence': 0,
                'word_count': 0,
                'regions': [],
                'type': 'image'
            }

        all_text = []
        regions = []
        confidences = []

        for idx, (box, (text, confidence)) in enumerate(ocr_results):
            if text and text.strip():
                all_text.append(text)
                confidences.append(confidence)

                # Extract bounding box coordinates
                box_coords = np.array(box).astype(int)
                x_min = int(np.min(box_coords[:, 0]))
                y_min = int(np.min(box_coords[:, 1]))
                x_max = int(np.max(box_coords[:, 0]))
                y_max = int(np.max(box_coords[:, 1]))
                width = x_max - x_min
                height = y_max - y_min

                regions.append({
                    'text': text.strip(),
                    'confidence': round(float(confidence), 2),
                    'bbox': {
                        'x': x_min,
                        'y': y_min,
                        'width': width,
                        'height': height
                    },
                    'position': self._classify_position(y_min, image_shape[0]),
                    'region_type': self._classify_region_type(text.strip())
                })

        avg_confidence = np.mean(confidences) if confidences else 0

        return {
            'text': '\n'.join(all_text),
            'confidence': round(float(avg_confidence), 2),
            'word_count': len(regions),
            'regions': regions,
            'type': 'image'
        }

    def _extract_key_data(self, regions: List[dict]) -> dict:
        """
        Smart extraction: Extract important data types from regions.
        Filters and categorizes text for better data extraction.
        """
        extracted = {
            'emails': [],
            'phones': [],
            'urls': [],
            'dates': [],
            'prices': [],
            'names': [],
            'addresses': [],
            'key_phrases': [],
            'logos_text': []
        }

        for region in regions:
            text = region['text']
            conf = region['confidence']

            # Only consider high-confidence text for extraction
            if conf < 0.5:
                continue

            # Email extraction
            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
            extracted['emails'].extend(emails)

            # Phone extraction (multiple formats)
            phones = re.findall(
                r'(?:\+?\d{1,3}[-.\s]?)?'
                r'(?:\(\d{3}\)|\d{3})[-.\s]?'
                r'\d{3}[-.\s]?\d{4}',
                text
            )
            extracted['phones'].extend(phones)

            # URL extraction
            urls = re.findall(r'https?://[^\s]+', text)
            extracted['urls'].extend(urls)

            # Date extraction (multiple formats)
            dates = re.findall(
                r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|'
                r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|'
                r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b',
                text, re.IGNORECASE
            )
            extracted['dates'].extend(dates)

            # Price/currency extraction
            prices = re.findall(r'(?:\$|€|£|¥|Rp)\s?[\d,]+\.?\d*', text)
            extracted['prices'].extend(prices)

            # Logo/company name detection (text in upper portion, often larger)
            if region['position'] == 'top' and (text.isupper() or len(text.split()) <= 3):
                extracted['logos_text'].append(text)

            # Address detection (text with street, road, st, ave, etc.)
            if re.search(r'\b(?:street|st|avenue|ave|road|rd|blvd|lane|ln|drive|dr|way|court|ct)\b\.?', text, re.IGNORECASE):
                extracted['addresses'].append(text)

            # Key phrases (important business terms)
            if re.search(r'\b(?:CEO|Director|Manager|President|Company|Inc|Corp|LLC|Ltd|Co)\b\.?', text, re.IGNORECASE):
                extracted['key_phrases'].append(text)

        # Deduplicate
        for key in extracted:
            extracted[key] = list(dict.fromkeys(extracted[key]))  # Preserve order

        return extracted

    def _classify_position(self, y_coord: int, image_height: int) -> str:
        """Classify text position in image."""
        if y_coord < image_height * 0.2:
            return 'top'
        elif y_coord < image_height * 0.5:
            return 'upper_middle'
        elif y_coord < image_height * 0.8:
            return 'lower_middle'
        else:
            return 'bottom'

    def _classify_region_type(self, text: str) -> str:
        """Classify the type of text region."""
        if re.match(r'^[\d\-\(\)\+\s\.]{7,}$', text):
            return 'phone_or_number'
        elif '@' in text:
            return 'email'
        elif text.startswith('http'):
            return 'url'
        elif re.search(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', text):
            return 'date'
        elif re.search(r'[\$€£¥]', text):
            return 'price'
        elif text.isupper() and len(text.split()) <= 4:
            return 'heading_or_logo'
        else:
            return 'text'

    def _preprocess_for_paddle(self, image_np: np.ndarray) -> np.ndarray:
        """Preprocess image for better PaddleOCR results."""
        # Convert to grayscale if color
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_np.copy()

        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Adaptive thresholding for better contrast
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Convert back to 3-channel for PaddleOCR
        result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

        return result

    def _merge_structured_data(self, pages_data: List[dict]) -> dict:
        """Merge structured data from multiple pages."""
        merged = {
            'emails': [],
            'phones': [],
            'urls': [],
            'dates': [],
            'prices': [],
            'names': [],
            'addresses': [],
            'key_phrases': [],
            'logos_text': []
        }

        for page in pages_data:
            if 'structured_data' in page and page['structured_data']:
                for key in merged:
                    if key in page['structured_data']:
                        merged[key].extend(page['structured_data'][key])

        # Deduplicate
        for key in merged:
            merged[key] = list(dict.fromkeys(merged[key]))

        return merged

    def get_supported_languages(self) -> list:
        """Get list of supported languages."""
        return ['en', 'ch', 'french', 'german', 'japan', 'korean', 'ta', 'te', 'ru']


# Default instance with smart extraction enabled
ocr_engine = OCREngine(enable_smart_extraction=True)
