"""Application settings for the Finance OCR backend."""

from dataclasses import dataclass
import os


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value.strip())


@dataclass(frozen=True)
class AppSettings:
    backend_port: int = env_int("OCR_BACKEND_PORT", 8001)
    ocr_detection_model: str = os.getenv("OCR_DET_MODEL", "PP-OCRv5_mobile_det")
    ocr_recognition_model: str = os.getenv("OCR_REC_MODEL", "PP-OCRv5_mobile_rec")
    ocr_device: str = os.getenv("OCR_DEVICE", "cpu")
    ocr_textline_orientation: bool = env_bool("OCR_TEXTLINE_ORIENTATION", False)
    ocr_doc_orientation_classify: bool = env_bool("OCR_DOC_ORIENTATION_CLASSIFY", False)
    ocr_doc_unwarping: bool = env_bool("OCR_DOC_UNWARPING", False)
    pdf_dpi: int = env_int("OCR_PDF_DPI", 150)
    preprocess_enabled: bool = env_bool("OCR_PREPROCESS", True)
    finance_extraction_enabled: bool = env_bool("OCR_FINANCE_EXTRACTION", True)


settings = AppSettings()
