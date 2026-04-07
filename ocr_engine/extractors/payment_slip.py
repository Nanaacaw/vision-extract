"""
Payment slip document extractor.
Extracts bank transfer/payment slip data including payer, payee, and amount.
"""

import re
from typing import Dict, Any, List, Optional
from ..extractors.base import BaseExtractor, ExtractionResult


class PaymentSlipExtractor(BaseExtractor):
    """Extracts data from payment slips/bukti transfer."""
    
    def _get_doc_type(self) -> str:
        return 'payment_slip'
    
    def extract(self, text: str, ocr_regions: Optional[List[Dict]] = None) -> ExtractionResult:
        """Extract payment slip data from OCR text."""
        data = {
            'bank_name': self._extract_bank_name(text),
            'transfer_date': self._extract_transfer_date(text),
            'transfer_time': self._extract_transfer_time(text),
            'reference_number': self._extract_reference_number(text),
            'payer_name': self._extract_payer_name(text),
            'payer_account': self._extract_payer_account(text),
            'payee_name': self._extract_payee_name(text),
            'payee_account': self._extract_payee_account(text),
            'amount': self._extract_amount(text),
            'currency': self._extract_currency(text),
            'transfer_type': self._extract_transfer_type(text),
            'swift_code': self._extract_swift_code(text),
            'description': self._extract_description(text),
            'status': self._extract_status(text)
        }
        
        # Validate
        validation_errors = self.validate(data)
        
        # Calculate confidence
        filled_fields = sum(1 for v in data.values() if v not in [None, '', 0])
        total_fields = len(data)
        confidence = (filled_fields / total_fields * 100) if total_fields > 0 else 0
        
        return ExtractionResult(
            doc_type='payment_slip',
            data=data,
            confidence=round(confidence, 2),
            validation_errors=validation_errors,
            raw_text=text
        )
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate payment slip data."""
        errors = []
        
        # Amount should be positive
        if data['amount'] and data['amount'] <= 0:
            errors.append("Transfer amount is zero or negative")
        
        # Payer and payee should be different
        if data['payer_name'] and data['payee_name']:
            if data['payer_name'].lower() == data['payee_name'].lower():
                errors.append("Payer and payee names are identical")
        
        # Reference number should exist
        if not data['reference_number']:
            errors.append("Reference number not found")
        
        return errors
    
    def _extract_bank_name(self, text: str) -> Optional[str]:
        """Extract bank name."""
        patterns = [
            r'(?:bank\s*name|bank)[:\s]+([A-Za-z\s&,.]+?)(?:\n|$)',
            r'(?:bukti\s*transfer|transfer\s*slip)\s+([A-Za-z\s]+?)(?:\n|$)',
        ]
        
        # Common Indonesian banks
        banks = ['BCA', 'Mandiri', 'BNI', 'BRI', 'CIMB', 'Danamon', 'Permata', 'HSBC', 'Citibank']
        text_upper = text.upper()
        for bank in banks:
            if bank in text_upper:
                return bank
        
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_transfer_date(self, text: str) -> Optional[str]:
        """Extract transfer date."""
        patterns = [
            r'(?:date|tanggal\s*transfer)[:\s]*(\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
            r'(?:date|tanggal)[:\s]*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_transfer_time(self, text: str) -> Optional[str]:
        """Extract transfer time."""
        patterns = [
            r'(?:time|waktu)[:\s]*(\d{1,2}:\d{2}(?::\d{2})?)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_reference_number(self, text: str) -> Optional[str]:
        """Extract reference/transaction number."""
        patterns = [
            r'(?:reference|ref|txn\s*(?:id|no)|transaction\s*id)[:\s]*([A-Za-z0-9\-\/]+)',
            r'(?:no\s*referensi|kode\s*transaksi)[:\s]*([A-Za-z0-9\-\/]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_payer_name(self, text: str) -> Optional[str]:
        """Extract payer/sender name."""
        patterns = [
            r'(?:from|pengirim|debit\s*from|payer)[:\s]+([A-Za-z\s&,.]+?)(?:\n|$)',
            r'(?:rekening\s*sumber|nama\s*pengirim)[:\s]+([^\n]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_payer_account(self, text: str) -> Optional[str]:
        """Extract payer account number."""
        patterns = [
            r'(?:from\s*account|pengirim\s*account|no\s*rek\s*sumber)[:\s]*([\d\-]+)',
            r'(?:rekening\s*sumber|no\s*rek)[:\s]*([\d\-]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_payee_name(self, text: str) -> Optional[str]:
        """Extract payee/recipient name."""
        patterns = [
            r'(?:to|penerima|credit\s*to|payee|beneficiary)[:\s]+([A-Za-z\s&,.]+?)(?:\n|$)',
            r'(?:rekening\s*tujuan|nama\s*penerima)[:\s]+([^\n]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_payee_account(self, text: str) -> Optional[str]:
        """Extract payee account number."""
        patterns = [
            r'(?:to\s*account|penerima\s*account|rekening\s*tujuan|no\s*rek\s*tujuan)[:\s]*([\d\-]+)',
            r'(?:account\s*no|rek\s*no)[:\s]*([\d\-]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract transfer amount."""
        patterns = [
            r'(?:amount|jumlah|transfer\s*amount|amount\s*transfer|nominal)[:\s]*[\$RpIDR]*\s*([\d,]+\.?\d*)',
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
        return None
    
    def _extract_transfer_type(self, text: str) -> Optional[str]:
        """Extract transfer type."""
        types = ['online', 'realtime', 'rtgs', 'kliring', 'internal', 'skn', 'bi-fast']
        text_lower = text.lower()
        
        for t in types:
            if t in text_lower:
                return t.upper()
        return None
    
    def _extract_swift_code(self, text: str) -> Optional[str]:
        """Extract SWIFT/BIC code."""
        patterns = [
            r'(?:swift|bic|swift\s*bic)[:\s]*([A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_description(self, text: str) -> Optional[str]:
        """Extract transfer description/notes."""
        patterns = [
            r'(?:description|keterangan|berita)[:\s]+([^\n]+)',
            r'(?:remark|catatan)[:\s]+([^\n]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_status(self, text: str) -> Optional[str]:
        """Extract transfer status."""
        statuses = ['success', 'berhasil', 'pending', 'gagal', 'failed', 'completed']
        text_lower = text.lower()
        
        for status in statuses:
            if status in text_lower:
                return status
        return None
