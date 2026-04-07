"""
Image preprocessing utilities for better OCR accuracy.
"""

import cv2
import numpy as np
from PIL import Image
import io


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Apply preprocessing to improve OCR accuracy.
    
    Args:
        image: PIL Image
        
    Returns:
        Preprocessed PIL Image
    """
    opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
    
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    sharpen_kernel = np.array([[0, -1, 0],
                               [-1, 5, -1],
                               [0, -1, 0]])
    sharpened = cv2.filter2D(cleaned, -1, sharpen_kernel)
    
    pil_image = Image.fromarray(sharpened)
    
    return pil_image


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
    
    return Image.fromarray(enhanced)
