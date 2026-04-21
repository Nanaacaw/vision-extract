"""Application settings for the Finance OCR backend."""

from dataclasses import dataclass
import os
from pathlib import Path


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


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
    ocr_return_word_box: bool = env_bool("OCR_RETURN_WORD_BOX", True)
    pdf_dpi: int = env_int("OCR_PDF_DPI", 150)
    preprocess_enabled: bool = env_bool("OCR_PREPROCESS", True)
    finance_extraction_enabled: bool = env_bool("OCR_FINANCE_EXTRACTION", True)


settings = AppSettings()
