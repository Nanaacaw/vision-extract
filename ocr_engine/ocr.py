import cv2
import numpy as np
from PIL import Image
import io
import fitz
from typing import Optional, List, Dict
from paddleocr import PaddleOCR
import logging

from .document_classifier import classifier
from .document import Document, Block, ExtractedField
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
    """Advanced OCR engine with canonical document representation."""

    def __init__(
        self,
        language: str = 'en',
        use_angle_cls: bool = True,
        use_gpu: bool = False,
        enable_finance_extraction: bool = True
    ):
        self.language = language
        self.enable_finance_extraction = enable_finance_extraction

        # Initialize extractors
        self.invoice_extractor = InvoiceExtractor()
        self.receipt_extractor = ReceiptExtractor()
        self.payment_slip_extractor = PaymentSlipExtractor()
        self.tax_invoice_extractor = TaxInvoiceExtractor()
        self.reimbursement_extractor = ReimbursementExtractor()
        self.validator = FinanceValidator()

        # Initialize PaddleOCR (v2.8.1 uses PP-OCRv5 by default)
        # PP-OCRv5 offers improved accuracy and speed over v4
        self.ocr = PaddleOCR(
            use_angle_cls=use_angle_cls,
            lang=language,
            use_gpu=use_gpu,
            show_log=False
        )

    def extract_text(self, image_data: bytes, preprocess: bool = True) -> str:
        """Extract plain text."""
        doc = self.extract_document(image_data, preprocess=preprocess)
        return doc.render_full_text()

    def extract_document(self, file_data: bytes, preprocess: bool = True, is_pdf: bool = False) -> Document:
        """
        Extract document with canonical representation.
        Returns a Document object that can render to multiple formats.
        """
        try:
            if is_pdf:
                return self._extract_from_pdf(file_data, preprocess)
            else:
                return self._extract_from_image(file_data, preprocess)
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}", exc_info=True)
            raise

    def _extract_from_image(self, image_data: bytes, preprocess: bool = True) -> Document:
        """Extract from image file."""
        image = Image.open(io.BytesIO(image_data))
        image_np = np.array(image)
        
        if len(image_np.shape) == 3 and image_np.shape[2] == 4:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)
        
        if preprocess:
            image_np = self._preprocess_for_paddle(image_np)
        
        # Run OCR
        ocr_result = self.ocr.ocr(image_np, cls=True)
        
        # Build document
        doc = Document()
        doc.page_count = 1
        
        words = []
        if ocr_result and ocr_result[0]:
            for idx, (box, (text, confidence)) in enumerate(ocr_result[0]):
                if text and text.strip():
                    box_coords = np.array(box).astype(int)
                    words.append({
                        'text': text.strip(),
                        'confidence': round(float(confidence), 2),
                        'bbox': {
                            'x': int(np.min(box_coords[:, 0])),
                            'y': int(np.min(box_coords[:, 1])),
                            'width': int(np.max(box_coords[:, 0])) - int(np.min(box_coords[:, 0])),
                            'height': int(np.max(box_coords[:, 1])) - int(np.min(box_coords[:, 1]))
                        },
                        'page': 1
                    })
        
        doc.add_blocks_from_ocr(words, page=1)
        
        # Classify and extract finance data if enabled
        full_text = doc.render_full_text()
        if self.enable_finance_extraction and full_text.strip():
            classification = classifier.classify(full_text)
            if classification.doc_type != 'unknown':
                doc.doc_type = classification.doc_type
                doc.classification_confidence = classification.confidence
                
                extractor = self._get_extractor(classification.doc_type)
                if extractor:
                    extraction = extractor.extract(full_text)
                    doc.metadata['finance_data'] = extraction.data
                    
                    # Add as extracted fields
                    for key, value in extraction.data.items():
                        if value and isinstance(value, (str, int, float)):
                            doc.add_field(ExtractedField(
                                name=key.replace('_', ' ').title(),
                                value=str(value),
                                confidence=extraction.confidence
                            ))
        
        return doc

    def _extract_from_pdf(self, pdf_data: bytes, preprocess: bool = True, dpi: int = 150) -> Document:
        """Extract from PDF file."""
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        num_pages = len(pdf_document)
        
        doc = Document()
        doc.page_count = num_pages
        
        all_words = []
        
        for page_num in range(num_pages):
            page = pdf_document[page_num]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            
            img_data = pix.tobytes("png")
            image_np = np.frombuffer(img_data, dtype=np.uint8)
            image_np = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
            
            if preprocess:
                image_np = self._preprocess_for_paddle(image_np)
            
            try:
                ocr_result = self.ocr.ocr(image_np, cls=True)
            except Exception as e:
                logger.error(f"OCR error on page {page_num + 1}: {str(e)}")
                continue
            
            if ocr_result and ocr_result[0]:
                for box, (text, confidence) in ocr_result[0]:
                    if text and text.strip():
                        box_coords = np.array(box).astype(int)
                        all_words.append({
                            'text': text.strip(),
                            'confidence': round(float(confidence), 2),
                            'bbox': {
                                'x': int(np.min(box_coords[:, 0])),
                                'y': int(np.min(box_coords[:, 1])),
                                'width': int(np.max(box_coords[:, 0])) - int(np.min(box_coords[:, 0])),
                                'height': int(np.max(box_coords[:, 1])) - int(np.min(box_coords[:, 1]))
                            },
                            'page': page_num + 1
                        })
        
        pdf_document.close()
        
        # Add blocks to document
        for word in all_words:
            block = Block(
                text=word['text'],
                bbox=word['bbox'],
                confidence=word['confidence'],
                page=word['page']
            )
            doc.add_block(block)
        
        # Classify and extract finance data
        full_text = doc.render_full_text()
        if self.enable_finance_extraction and full_text.strip():
            classification = classifier.classify(full_text)
            if classification.doc_type != 'unknown':
                doc.doc_type = classification.doc_type
                doc.classification_confidence = classification.confidence
                
                extractor = self._get_extractor(classification.doc_type)
                if extractor:
                    extraction = extractor.extract(full_text)
                    doc.metadata['finance_data'] = extraction.data
                    
                    for key, value in extraction.data.items():
                        if value and isinstance(value, (str, int, float)):
                            doc.add_field(ExtractedField(
                                name=key.replace('_', ' ').title(),
                                value=str(value),
                                confidence=extraction.confidence
                            ))
        
        return doc

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

    def _preprocess_for_paddle(self, image_np: np.ndarray) -> np.ndarray:
        """Preprocess image for PaddleOCR."""
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_np.copy()
        
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


# Default instance
ocr_engine = OCREngine(enable_finance_extraction=True)
