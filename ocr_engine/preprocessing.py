import cv2
import numpy as np

"""Geometry-preserving preprocessing profiles for PaddleOCR."""

PreprocessProfile = str
VALID_PROFILES = {"auto", "none", "clean", "receipt", "camera"}


def resolve_profile(profile: str | None, file_type: str) -> PreprocessProfile:
    normalized = (profile or "auto").strip().lower()
    if normalized not in VALID_PROFILES:
        return "auto"
    if normalized != "auto":
        return normalized
    return "clean" if file_type == "pdf" else "receipt"


def apply_preprocessing(
    image_np: np.ndarray,
    profile: str | None = "auto",
    file_type: str = "image",
) -> np.ndarray:
    """Apply a profile without changing image dimensions, so OCR boxes stay aligned."""
    resolved = resolve_profile(profile, file_type)
    if resolved == "none":
        return image_np
    if resolved == "clean":
        return _clean_scan(image_np)
    if resolved == "camera":
        return _camera_photo(image_np)
    return _receipt(image_np)


def _to_gray(image_np: np.ndarray) -> np.ndarray:
    if len(image_np.shape) == 2:
        return image_np.copy()
    return cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)


def _to_bgr(gray: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _clahe(gray: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _sharpen(gray: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(gray, (0, 0), 1.0)
    return cv2.addWeighted(gray, 1.45, blur, -0.45, 0)


def _clean_scan(image_np: np.ndarray) -> np.ndarray:
    gray = _to_gray(image_np)
    enhanced = _clahe(gray, clip_limit=1.6)
    return _to_bgr(enhanced)


def _receipt(image_np: np.ndarray) -> np.ndarray:
    gray = _to_gray(image_np)
    denoised = cv2.fastNlMeansDenoising(gray, None, 7, 7, 21)
    enhanced = _clahe(denoised, clip_limit=2.2)
    sharpened = _sharpen(enhanced)
    return _to_bgr(sharpened)


def _camera_photo(image_np: np.ndarray) -> np.ndarray:
    gray = _to_gray(image_np)
    denoised = cv2.fastNlMeansDenoising(gray, None, 9, 7, 21)
    enhanced = _clahe(denoised, clip_limit=2.6)
    sharpened = _sharpen(enhanced)
    binary = cv2.adaptiveThreshold(
        sharpened,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        17,
        4,
    )
    return _to_bgr(binary)
