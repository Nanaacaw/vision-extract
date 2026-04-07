"""
Image preprocessing utilities optimized for PaddleOCR.
"""

import cv2
import numpy as np
from PIL import Image
import io


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Apply preprocessing optimized for PaddleOCR.

    Args:
        image: PIL Image

    Returns:
        Preprocessed PIL Image
    """
    opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    # Adaptive thresholding for better contrast
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Convert back to 3-channel for PaddleOCR
    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    return Image.fromarray(result)


def denoise_image(image: Image.Image) -> Image.Image:
    """
    Remove noise from image.

    Args:
        image: PIL Image

    Returns:
        Denoised PIL Image
    """
    opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)

    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    return Image.fromarray(denoised)


def resize_image(image: Image.Image, scale_factor: float = 2.0) -> Image.Image:
    """
    Resize image for better OCR on small text.

    Args:
        image: PIL Image
        scale_factor: Factor to scale the image

    Returns:
        Resized PIL Image
    """
    width = int(image.width * scale_factor)
    height = int(image.height * scale_factor)

    resized = image.resize((width, height), Image.LANCZOS)
    return resized


def enhance_contrast(image: Image.Image) -> Image.Image:
    """
    Enhance image contrast for better text recognition.

    Args:
        image: PIL Image

    Returns:
        Contrast-enhanced PIL Image
    """
    opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)

    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Convert to 3-channel
    enhanced_3ch = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

    return Image.fromarray(enhanced_3ch)


def deskew_image(image: Image.Image) -> Image.Image:
    """
    Deskew/rotate image to straighten text.

    Args:
        image: PIL Image

    Returns:
        Deskewed PIL Image
    """
    opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)

    # Detect angle
    coords = np.column_stack(np.where(gray > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Rotate
        (h, w) = opencv_image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(opencv_image, M, (w, h),
                                 flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        return Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))

    return image


def remove_background(image: Image.Image) -> Image.Image:
    """
    Remove background noise for cleaner text extraction.

    Args:
        image: PIL Image

    Returns:
        PIL Image with reduced background noise
    """
    opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)

    # Morphological opening to remove small objects
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    opening = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel, iterations=2)

    # Dilate to strengthen text
    dilated = cv2.dilate(opening, kernel, iterations=1)

    # Convert to 3-channel
    result = cv2.cvtColor(dilated, cv2.COLOR_GRAY2BGR)

    return Image.fromarray(result)
