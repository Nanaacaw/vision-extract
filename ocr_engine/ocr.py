import io
import logging
from typing import Any

import cv2
import fitz
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image

from .document import Block, Document, ExtractedField
from .document_classifier import classifier
from .extractors import (
    InvoiceExtractor,
    PaymentSlipExtractor,
    ReceiptExtractor,
    ReimbursementExtractor,
    TaxInvoiceExtractor,
)
from .settings import AppSettings, settings
from .validators.finance import FinanceValidator

logger = logging.getLogger(__name__)


class OCREngine:
    """OCR engine for PP-OCRv5 finance document extraction."""

    def __init__(self, config: AppSettings = settings):
        self.config = config
        self.ocr = PaddleOCR(
            text_detection_model_name=config.ocr_detection_model,
            text_recognition_model_name=config.ocr_recognition_model,
            use_doc_orientation_classify=config.ocr_doc_orientation_classify,
            use_doc_unwarping=config.ocr_doc_unwarping,
            use_textline_orientation=config.ocr_textline_orientation,
            device=config.ocr_device,
        )

        self.invoice_extractor = InvoiceExtractor()
        self.receipt_extractor = ReceiptExtractor()
        self.payment_slip_extractor = PaymentSlipExtractor()
        self.tax_invoice_extractor = TaxInvoiceExtractor()
        self.reimbursement_extractor = ReimbursementExtractor()
        self.validator = FinanceValidator()

    def extract_text(self, image_data: bytes, preprocess: bool | None = None) -> str:
        """Extract plain text."""
        doc = self.extract_document(image_data, preprocess=preprocess)
        return doc.render_full_text()

    def extract_document(
        self,
        file_data: bytes,
        preprocess: bool | None = None,
        is_pdf: bool = False,
    ) -> Document:
        """Extract a canonical document from image or PDF bytes."""
        try:
            should_preprocess = self.config.preprocess_enabled if preprocess is None else preprocess
            if is_pdf:
                doc = self._extract_from_pdf(file_data, should_preprocess)
            else:
                doc = self._extract_from_image(file_data, should_preprocess)

            self._apply_finance_extraction(doc)
            return doc
        except Exception as exc:
            logger.error("Extraction error: %s", str(exc), exc_info=True)
            raise

    def _extract_from_image(self, image_data: bytes, preprocess: bool) -> Document:
        image_np = self._decode_image(image_data)
        if preprocess:
            image_np = self._preprocess_for_paddle(image_np)

        doc = Document()
        doc.page_count = 1
        doc.add_blocks_from_ocr(self._extract_words(image_np, page=1), page=1)
        return doc

    def _extract_from_pdf(self, pdf_data: bytes, preprocess: bool) -> Document:
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        doc = Document()
        doc.page_count = len(pdf_document)

        try:
            for page_index in range(doc.page_count):
                image_np = self._render_pdf_page(pdf_document[page_index])
                if preprocess:
                    image_np = self._preprocess_for_paddle(image_np)

                for word in self._extract_words(image_np, page=page_index + 1):
                    doc.add_block(
                        Block(
                            text=word["text"],
                            bbox=word["bbox"],
                            confidence=word["confidence"],
                            page=word["page"],
                        )
                    )
        finally:
            pdf_document.close()

        return doc

    def _extract_words(self, image_np: np.ndarray, page: int) -> list[dict[str, Any]]:
        ocr_result = self.ocr.predict(input=image_np)
        words: list[dict[str, Any]] = []

        for result in self._as_list(ocr_result):
            data = self._result_to_dict(result)
            if isinstance(data.get("res"), dict):
                data = data["res"]

            texts = self._as_list(data.get("rec_texts"))
            scores = self._as_list(data.get("rec_scores"))
            boxes = self._as_list(self._ocr_boxes(data))

            for index, text in enumerate(texts):
                clean_text = str(text).strip()
                if not clean_text:
                    continue

                score = scores[index] if index < len(scores) else 0.0
                box = boxes[index] if index < len(boxes) else None
                words.append({
                    "text": clean_text,
                    "confidence": round(float(score), 2),
                    "bbox": self._bbox_from_ocr_box(box),
                    "page": page,
                })

        return words

    def _apply_finance_extraction(self, doc: Document) -> None:
        if not self.config.finance_extraction_enabled:
            return

        full_text = doc.render_full_text()
        if not full_text.strip():
            return

        classification = classifier.classify(full_text)
        if classification.doc_type == "unknown":
            return

        doc.doc_type = classification.doc_type
        doc.classification_confidence = classification.confidence

        extractor = self._get_extractor(classification.doc_type)
        if not extractor:
            return

        extraction = extractor.extract(full_text)
        doc.metadata["finance_data"] = extraction.data

        for key, value in extraction.data.items():
            if value and isinstance(value, (str, int, float)):
                doc.add_field(
                    ExtractedField(
                        name=key.replace("_", " ").title(),
                        value=str(value),
                        confidence=extraction.confidence,
                    )
                )

    def _get_extractor(self, doc_type: str):
        extractors = {
            "invoice": self.invoice_extractor,
            "receipt": self.receipt_extractor,
            "payment_slip": self.payment_slip_extractor,
            "tax_invoice": self.tax_invoice_extractor,
            "reimbursement": self.reimbursement_extractor,
        }
        return extractors.get(doc_type)

    def _render_pdf_page(self, page: fitz.Page) -> np.ndarray:
        mat = fitz.Matrix(self.config.pdf_dpi / 72, self.config.pdf_dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        image_np = np.frombuffer(img_data, dtype=np.uint8)
        return cv2.imdecode(image_np, cv2.IMREAD_COLOR)

    @staticmethod
    def _decode_image(image_data: bytes) -> np.ndarray:
        image = Image.open(io.BytesIO(image_data))
        image_np = np.array(image)

        if len(image_np.shape) == 3 and image_np.shape[2] == 4:
            return cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)

        return image_np

    @staticmethod
    def _preprocess_for_paddle(image_np: np.ndarray) -> np.ndarray:
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_np.copy()

        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        binary = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    @staticmethod
    def _result_to_dict(result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result

        json_value = getattr(result, "json", None)
        if callable(json_value):
            json_value = json_value()
        if isinstance(json_value, dict):
            return json_value

        to_dict = getattr(result, "to_dict", None)
        if callable(to_dict):
            value = to_dict()
            if isinstance(value, dict):
                return value

        return {}

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if hasattr(value, "tolist"):
            return value.tolist()
        return [value]

    @staticmethod
    def _ocr_boxes(data: dict[str, Any]) -> Any:
        if data.get("rec_polys") is not None:
            return data["rec_polys"]
        return data.get("rec_boxes")

    @staticmethod
    def _bbox_from_ocr_box(box: Any) -> dict[str, int]:
        if box is None:
            return {"x": 0, "y": 0, "width": 0, "height": 0}

        box_array = np.array(box, dtype=float)
        if box_array.size == 4 and box_array.ndim == 1:
            x_min, y_min, x_max, y_max = box_array
        elif box_array.ndim >= 2 and box_array.shape[-1] >= 2:
            x_min = float(np.min(box_array[..., 0]))
            y_min = float(np.min(box_array[..., 1]))
            x_max = float(np.max(box_array[..., 0]))
            y_max = float(np.max(box_array[..., 1]))
        else:
            return {"x": 0, "y": 0, "width": 0, "height": 0}

        return {
            "x": int(round(x_min)),
            "y": int(round(y_min)),
            "width": max(0, int(round(x_max - x_min))),
            "height": max(0, int(round(y_max - y_min))),
        }


ocr_engine = OCREngine()
