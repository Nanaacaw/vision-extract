"""Geometry-preserving preprocessing profiles for PaddleOCR."""

from dataclasses import dataclass

import cv2
import numpy as np

PreprocessProfile = str
VALID_PROFILES = {"auto", "none", "clean", "receipt", "camera"}


@dataclass(frozen=True)
class CropRegion:
    x: int
    y: int
    width: int
    height: int
    applied: bool = False

    def as_dict(self) -> dict[str, int | bool]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "applied": self.applied,
        }


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


def crop_document_region(image_np: np.ndarray, padding: int = 18) -> tuple[np.ndarray, CropRegion]:
    """Crop likely document region without rotating or warping the image."""
    height, width = image_np.shape[:2]
    full_region = CropRegion(0, 0, width, height, applied=False)
    if width < 160 or height < 160:
        return image_np, full_region

    gray = _to_gray(image_np)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image_np, full_region

    image_area = width * height
    candidates = []
    for contour in contours:
        x, y, crop_width, crop_height = cv2.boundingRect(contour)
        area = crop_width * crop_height
        if area < image_area * 0.08 or area > image_area * 0.96:
            continue
        aspect_ratio = crop_width / max(crop_height, 1)
        if aspect_ratio < 0.18 or aspect_ratio > 5.5:
            continue
        candidates.append((area, x, y, crop_width, crop_height))

    if not candidates:
        return image_np, full_region

    _, x, y, crop_width, crop_height = max(candidates, key=lambda item: item[0])
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(width, x + crop_width + padding)
    y2 = min(height, y + crop_height + padding)
    if (x2 - x1) >= width * 0.96 and (y2 - y1) >= height * 0.96:
        return image_np, full_region

    region = CropRegion(x1, y1, x2 - x1, y2 - y1, applied=True)
    return image_np[y1:y2, x1:x2].copy(), region


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
