"""Text cleanup helpers for noisy OCR output."""

import re
import unicodedata

SEPARATOR_RE = re.compile(r"^[\s=|\-_:;,.~`]+$")
REPEATED_SYMBOL_RE = re.compile(r"([=|\-_:;,.~`])\1{2,}")
SPACE_RE = re.compile(r"[ \t]+")
LOGO_LABEL_RE = re.compile(r"^[\w\s.-]{0,40}logo$", re.IGNORECASE)
ICON_LABEL_RE = re.compile(r"^image\s*:\s*.*icon$", re.IGNORECASE)
PARSER_LABELS = {"picture", "text", "sectionheader", "section header"}
MEANINGFUL_SYMBOL_VALUES = {"*", "**", "***", "****", "*****", "#"}


def clean_ocr_text(text: str) -> str:
    """Normalize OCR text while preserving meaningful masked finance values."""
    normalized = unicodedata.normalize("NFKC", text or "")
    lines = []

    for line in normalized.replace("\r", "\n").split("\n"):
        clean_line = SPACE_RE.sub(" ", line).strip()
        if not clean_line or is_noise_text(clean_line):
            continue
        lines.append(clean_line)

    return " ".join(lines).strip()


def is_noise_text(text: str) -> bool:
    """Return True for decorative separators and symbol-only OCR artifacts."""
    value = SPACE_RE.sub(" ", text or "").strip()
    if not value:
        return True

    lower = value.lower().replace("_", " ")
    if lower in PARSER_LABELS:
        return True

    if LOGO_LABEL_RE.fullmatch(value) or ICON_LABEL_RE.fullmatch(value):
        return True

    if len(value) <= 1 and not value.isalnum():
        return True

    if SEPARATOR_RE.fullmatch(value) and (len(value) >= 3 or REPEATED_SYMBOL_RE.search(value)):
        return True

    alpha_num_count = sum(char.isalnum() for char in value)
    symbol_count = sum(not char.isalnum() and not char.isspace() for char in value)
    return alpha_num_count == 0 and symbol_count >= 2


def is_punctuation_noise(text: str) -> bool:
    """Return True for standalone punctuation that should not become review blocks."""
    value = SPACE_RE.sub(" ", text or "").strip()
    if not value or any(char.isalnum() for char in value):
        return False
    if value in MEANINGFUL_SYMBOL_VALUES:
        return False
    return len(value) <= 4 or SEPARATOR_RE.fullmatch(value) is not None


def split_review_words(text: str) -> list[str]:
    """Split a cleaned OCR block into reviewable word tokens."""
    return [part for part in SPACE_RE.split(text.strip()) if part]
