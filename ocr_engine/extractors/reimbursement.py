"""
Reimbursement document extractor.
Extracts employee reimbursement/expense claim data.
"""

import re
from typing import Dict, Any, List, Optional
from ..extractors.base import BaseExtractor, ExtractionResult


class ReimbursementExtractor(BaseExtractor):
    """Extracts data from reimbursement/expense claim documents."""
    
    def _get_doc_type(self) -> str:
        return 'reimbursement'
    
    def extract(self, text: str, ocr_regions: Optional[List[Dict]] = None) -> ExtractionResult:
        """Extract reimbursement data from OCR text."""
        data = {
            'employee_name': self._extract_employee_name(text),
            'employee_id': self._extract_employee_id(text),
            'department': self._extract_department(text),
            'claim_number': self._extract_claim_number(text),
            'claim_date': self._extract_claim_date(text),
            'expense_type': self._extract_expense_type(text),
            'expense_date': self._extract_expense_date(text),
            'description': self._extract_description(text),
            'amount': self._extract_amount(text),
            'currency': self._extract_currency(text),
            'receipt_count': self._extract_receipt_count(text),
            'project_code': self._extract_project_code(text),
            'manager_name': self._extract_manager_name(text),
            'approval_status': self._extract_approval_status(text),
            'payment_status': self._extract_payment_status(text),
            'notes': self._extract_notes(text)
        }
        
        # Validate
        validation_errors = self.validate(data)
        
        # Calculate confidence
        filled_fields = sum(1 for v in data.values() if v not in [None, '', 0])
        total_fields = len(data)
        confidence = (filled_fields / total_fields * 100) if total_fields > 0 else 0
        
        return ExtractionResult(
            doc_type='reimbursement',
            data=data,
            confidence=round(confidence, 2),
            validation_errors=validation_errors,
            raw_text=text
        )
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate reimbursement data."""
        errors = []
        
        # Amount should be positive
        if data['amount'] and data['amount'] <= 0:
            errors.append("Claim amount is zero or negative")
        
        # Employee info should exist
        if not data['employee_name']:
            errors.append("Employee name not found")
        
        # Approval status check
        if data['approval_status'] and data['approval_status'].lower() in ['rejected', 'ditolak']:
            data['warnings'] = ["Claim has been rejected"]
        
        return errors
    
    def _extract_employee_name(self, text: str) -> Optional[str]:
        """Extract employee name."""
        patterns = [
            r'(?:employee\s*name|nama\s*karyawan|name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'(?:karyawan|employee)[:\s]+([A-Z][A-Za-z\s]+?)(?:\n|$)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_employee_id(self, text: str) -> Optional[str]:
        """Extract employee ID/number."""
        patterns = [
            r'(?:employee\s*id|emp\s*id|nik|nomor\s*induk)[:\s]*([A-Za-z0-9\-]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_department(self, text: str) -> Optional[str]:
        """Extract department."""
        patterns = [
            r'(?:department|dept|departemen|divisi)[:\s]+([A-Za-z\s&,.]+?)(?:\n|$)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_claim_number(self, text: str) -> Optional[str]:
        """Extract claim/reimbursement number."""
        patterns = [
            r'(?:claim\s*(?:no|number|#)|reimbursement\s*no|expense\s*no)[:\s]*([A-Za-z0-9\-\/]+)',
            r'(?:nomor\s*klaim|no\s*pengajuan)[:\s]*([A-Za-z0-9\-\/]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_claim_date(self, text: str) -> Optional[str]:
        """Extract claim submission date."""
        patterns = [
            r'(?:claim\s*date|submission\s*date|tanggal\s*pengajuan)[:\s]*(\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
            r'(?:date|tanggal)[:\s]*(\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_expense_type(self, text: str) -> Optional[str]:
        """Extract expense category/type."""
        types = [
            'travel', 'travel expense', 'perjalanan dinas',
            'meal', 'meal expense', 'makan',
            'accommodation', 'hotel', 'penginapan',
            'transportation', 'transport', 'transportasi',
            'office supplies', 'perlengkapan kantor',
            'entertainment', 'hiburan',
            'medical', 'medis', 'kesehatan'
        ]
        text_lower = text.lower()
        
        for t in types:
            if t in text_lower:
                return t
        return None
    
    def _extract_expense_date(self, text: str) -> Optional[str]:
        """Extract expense occurrence date."""
        patterns = [
            r'(?:expense\s*date|tanggal\s*biaya)[:\s]*(\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
            r'(?:transaction\s*date|tanggal\s*transaksi)[:\s]*(\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_description(self, text: str) -> Optional[str]:
        """Extract expense description."""
        patterns = [
            r'(?:description|keterangan|uraian|purpose)[:\s]+([^\n]+(?:\n[^\n]+){0,2})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract claim amount."""
        patterns = [
            r'(?:amount|jumlah|total\s*klaim|claim\s*amount)[:\s]*[\$RpIDR]*\s*([\d,]+\.?\d*)',
            r'(?:total\s*amount|jumlah\s*total)[:\s]*[\$RpIDR]*\s*([\d,]+\.?\d*)',
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
    
    def _extract_receipt_count(self, text: str) -> Optional[int]:
        """Extract number of receipts attached."""
        patterns = [
            r'(?:receipt\s*count|jumlah\s*struk|lampiran)[:\s]*(\d+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                try:
                    return int(match)
                except ValueError:
                    continue
        return None
    
    def _extract_project_code(self, text: str) -> Optional[str]:
        """Extract project code/number."""
        patterns = [
            r'(?:project\s*(?:code|no)|kode\s*proyek)[:\s]*([A-Za-z0-9\-\/]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_manager_name(self, text: str) -> Optional[str]:
        """Extract manager/supervisor name."""
        patterns = [
            r'(?:manager|supervisor|atasan|approved\s*by)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_approval_status(self, text: str) -> Optional[str]:
        """Extract approval status."""
        statuses = {
            'approved': r'approved|disetujui|disetujui',
            'pending': r'pending|menunggu|dalam\s*proses',
            'rejected': r'rejected|ditolak|tidak\s*disetujui',
            'submitted': r'submitted|diajukan|terkirim'
        }
        
        text_lower = text.lower()
        for status, pattern in statuses.items():
            if re.search(pattern, text_lower):
                return status
        return None
    
    def _extract_payment_status(self, text: str) -> Optional[str]:
        """Extract payment status."""
        statuses = {
            'paid': r'paid|dibayar|lunas',
            'unpaid': r'unpaid|belum\s*dibayar',
            'processing': r'processing|dalam\s*proses\s*pembayaran',
            'transferred': r'transferred|ditransfer'
        }
        
        text_lower = text.lower()
        for status, pattern in statuses.items():
            if re.search(pattern, text_lower):
                return status
        return None
    
    def _extract_notes(self, text: str) -> Optional[str]:
        """Extract notes/comments."""
        patterns = [
            r'(?:notes?|catatan|remarks?|keterangan\s*tambahan)[:\s]+([^\n]+(?:\n[^\n]+){0,3})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
