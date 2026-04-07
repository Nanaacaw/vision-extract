"""
Tax invoice (Faktur Pajak) document extractor.
Extracts Indonesian tax invoice data including NPWP, tax amounts, and taxable base.
"""

import re
from typing import Dict, Any, List, Optional
from ..extractors.base import BaseExtractor, ExtractionResult


class TaxInvoiceExtractor(BaseExtractor):
    """Extracts data from tax invoices/faktur pajak."""
    
    def _get_doc_type(self) -> str:
        return 'tax_invoice'
    
    def extract(self, text: str, ocr_regions: Optional[List[Dict]] = None) -> ExtractionResult:
        """Extract tax invoice data from OCR text."""
        data = {
            'faktur_number': self._extract_faktur_number(text),
            'npwp_seller': self._extract_npwp_seller(text),
            'npwp_buyer': self._extract_npwp_buyer(text),
            'seller_name': self._extract_seller_name(text),
            'seller_address': self._extract_seller_address(text),
            'buyer_name': self._extract_buyer_name(text),
            'buyer_address': self._extract_buyer_address(text),
            'tax_date': self._extract_tax_date(text),
            'dpp': self._extract_dpp(text),  # Dasar Pengenaan Pajak
            'tax_rate': self._extract_tax_rate(text),
            'ppn_amount': self._extract_ppn_amount(text),
            'total_with_tax': self._extract_total_with_tax(text),
            'currency': self._extract_currency(text),
            'barang_jasa': self._extract_barang_jasa(text),
            'faktur_type': self._extract_faktur_type(text)
        }
        
        # Validate
        validation_errors = self.validate(data)
        
        # Calculate confidence
        filled_fields = sum(1 for v in data.values() if v not in [None, '', 0])
        total_fields = len(data)
        confidence = (filled_fields / total_fields * 100) if total_fields > 0 else 0
        
        return ExtractionResult(
            doc_type='tax_invoice',
            data=data,
            confidence=round(confidence, 2),
            validation_errors=validation_errors,
            raw_text=text
        )
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate tax invoice data."""
        errors = []
        
        # NPWP format validation (15 digits: XX.XXX.XXX.X-XXX.XXX)
        if data['npwp_seller']:
            npwp_clean = re.sub(r'[.\-]', '', data['npwp_seller'])
            if not re.match(r'^\d{15}$', npwp_clean):
                errors.append(f"Invalid NPWP format: {data['npwp_seller']}")
        
        # Tax calculation validation
        if data['dpp'] and data['tax_rate'] and data['ppn_amount']:
            expected_ppn = data['dpp'] * (data['tax_rate'] / 100)
            if abs(expected_ppn - data['ppn_amount']) > 1:
                errors.append(f"PPN amount mismatch. Expected: {expected_ppn}, Got: {data['ppn_amount']}")
        
        # Total with tax validation
        if data['dpp'] and data['ppn_amount'] and data['total_with_tax']:
            expected_total = data['dpp'] + data['ppn_amount']
            if abs(expected_total - data['total_with_tax']) > 1:
                errors.append(f"Total with tax mismatch. Expected: {expected_total}, Got: {data['total_with_tax']}")
        
        return errors
    
    def _extract_faktur_number(self, text: str) -> Optional[str]:
        """Extract faktur pajak number."""
        patterns = [
            r'(?:nomor|no)\s*faktur[:\s]*([A-Za-z0-9\.\-\/]+)',
            r'faktur\s*(?:pajak\s*)?(?:no|number|#)[:\s]*([A-Za-z0-9\.\-\/]+)',
            r'kode\s*faktur[:\s]*([A-Za-z0-9\.\-\/]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_npwp_seller(self, text: str) -> Optional[str]:
        """Extract seller's NPWP (Tax ID)."""
        patterns = [
            r'npwp\s*(?:penjual|seller)[:\s]*([\d\.\-]+)',
            r'(?:npwp)[:\s]*([\d]{2}[\.\-]\d{3}[\.\-]\d{3}[\.\-]\d[\.\-]\d{3}[\.\-]\d{3})',
            r'(?:npwp)[:\s]*([\d\.\-]{15,20})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_npwp_buyer(self, text: str) -> Optional[str]:
        """Extract buyer's NPWP."""
        patterns = [
            r'npwp\s*(?:pembeli|buyer)[:\s]*([\d\.\-]+)',
            r'(?:npwp\s*pembeli)[:\s]*([\d\.\-]{15,20})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_seller_name(self, text: str) -> Optional[str]:
        """Extract seller name (PKP - Pengusaha Kena Pajak)."""
        patterns = [
            r'(?:nama|name)\s*penjual[:\s]+([^\n]+)',
            r'penjual[:\s]+([A-Z][A-Za-z\s&,.]+?)(?:\n|$)',
            r'(?:pkp|seller)[:\s]+([A-Z][A-Za-z\s&,.]+?)(?:\n|$)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_seller_address(self, text: str) -> Optional[str]:
        """Extract seller address."""
        patterns = [
            r'alamat\s*penjual[:\s]+([^\n]+)',
            r'(?:address|alamat)\s*seller[:\s]+([^\n]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_buyer_name(self, text: str) -> Optional[str]:
        """Extract buyer name."""
        patterns = [
            r'(?:nama|name)\s*pembeli[:\s]+([^\n]+)',
            r'pembeli[:\s]+([A-Z][A-Za-z\s&,.]+?)(?:\n|$)',
            r'(?:buyer|customer)[:\s]+([A-Z][A-Za-z\s&,.]+?)(?:\n|$)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_buyer_address(self, text: str) -> Optional[str]:
        """Extract buyer address."""
        patterns = [
            r'alamat\s*pembeli[:\s]+([^\n]+)',
            r'(?:address|alamat)\s*buyer[:\s]+([^\n]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_tax_date(self, text: str) -> Optional[str]:
        """Extract tax date."""
        patterns = [
            r'(?:tanggal\s*pajak|tax\s*date)[:\s]*(\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
            r'(?:tanggal\s*faktur|faktur\s*date)[:\s]*(\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_dpp(self, text: str) -> Optional[float]:
        """Extract DPP (Dasar Pengenaan Pajak / Taxable Base)."""
        patterns = [
            r'(?:dpp|dasar\s*pengenaan\s*pajak|taxable\s*base)[:\s]*[\$RpIDR]*\s*([\d,]+\.?\d*)',
            r'(?:jumlah\s*dpp)[:\s]*[\$RpIDR]*\s*([\d,]+\.?\d*)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                try:
                    return float(match.replace(',', ''))
                except ValueError:
                    continue
        return None
    
    def _extract_tax_rate(self, text: str) -> Optional[float]:
        """Extract tax rate percentage."""
        patterns = [
            r'(?:ppn|tax|vat)\s*(?:rate)?[:\s]*(\d+)%',
            r'(?:tarif\s*pajak|pajak)\s*(\d+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                try:
                    return float(match)
                except ValueError:
                    continue
        return None
    
    def _extract_ppn_amount(self, text: str) -> Optional[float]:
        """Extract PPN amount (VAT)."""
        patterns = [
            r'(?:ppn|pajak|vat)[:\s]*[\$RpIDR]*\s*([\d,]+\.?\d*)',
            r'(?:jumlah\s*ppn|ppn\s*amount)[:\s]*[\$RpIDR]*\s*([\d,]+\.?\d*)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                try:
                    return float(match.replace(',', ''))
                except ValueError:
                    continue
        return None
    
    def _extract_total_with_tax(self, text: str) -> Optional[float]:
        """Extract total with tax."""
        patterns = [
            r'(?:total\s*dengan\s*pajak|total\s*with\s*tax)[:\s]*[\$RpIDR]*\s*([\d,]+\.?\d*)',
            r'(?:jumlah\s*total|total)[:\s]*[\$RpIDR]*\s*([\d,]+\.?\d*)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                try:
                    return float(match.replace(',', ''))
                except ValueError:
                    continue
        return None
    
    def _extract_currency(self, text: str) -> Optional[str]:
        """Detect currency."""
        if re.search(r'Rp|IDR|rUpIaH', text, re.IGNORECASE):
            return 'IDR'
        elif re.search(r'\$', text):
            return 'USD'
        return 'IDR'
    
    def _extract_barang_jasa(self, text: str) -> List[Dict[str, Any]]:
        """Extract goods/services list."""
        items = []
        lines = text.split('\n')
        
        # Look for item lines
        for line in lines:
            line = line.strip()
            if any(kw in line.lower() for kw in ['barang', 'jasa', 'description', 'uraian']):
                continue
            if re.search(r'[\d,]+\.?\d*', line):
                items.append({'description': line})
        
        return items[:20]  # Limit to 20 items
    
    def _extract_faktur_type(self, text: str) -> Optional[str]:
        """Extract faktur type (normal, pengganti, pembatalan)."""
        types = ['normal', 'pengganti', 'pembatalan', 'replacement', 'cancellation']
        text_lower = text.lower()
        
        for t in types:
            if t in text_lower:
                return t
        return 'normal'
