"""
Base extractor interface for finance documents.
All specific extractors must inherit from this.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    """Standard result structure for all finance extractions."""
    doc_type: str
    data: Dict[str, Any]
    confidence: float
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    raw_text: str = ""


class BaseExtractor(ABC):
    """
    Abstract base class for all finance document extractors.
    Enforces consistent interface across all extractors.
    """
    
    def __init__(self):
        self.doc_type = self._get_doc_type()
    
    @abstractmethod
    def _get_doc_type(self) -> str:
        """Return document type identifier."""
        pass
    
    @abstractmethod
    def extract(self, text: str, ocr_regions: Optional[List[Dict]] = None) -> ExtractionResult:
        """
        Extract finance data from document text.
        
        Args:
            text: Full extracted text from OCR
            ocr_regions: Optional OCR region data for spatial context
            
        Returns:
            ExtractionResult with structured data
        """
        pass
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate extracted data.
        Returns list of validation error messages.
        
        Args:
            data: Extracted data dictionary
            
        Returns:
            List of validation error messages
        """
        pass
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        import re
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _find_pattern(self, text: str, pattern: str) -> Optional[str]:
        """Find first match of pattern in text."""
        import re
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip() if match.groups() else match.group(0).strip()
        return None
    
    def _find_all_patterns(self, text: str, pattern: str) -> List[str]:
        """Find all matches of pattern in text."""
        import re
        matches = re.findall(pattern, text, re.IGNORECASE)
        return [m.strip() if isinstance(m, str) else m[0].strip() for m in matches]
    
    def _extract_amount(self, text: str, label: str) -> Optional[float]:
        """
        Extract monetary amount from text near a label.
        Handles formats: 1,000.00, 1000, Rp 1000, IDR 1000
        """
        import re
        # Look for label followed by amount
        pattern = rf'{label}\s*[:;]?\s*[\$RpIDR]*\s*([\d,]+\.?\d*)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                return float(amount_str)
            except ValueError:
                return None
        return None
