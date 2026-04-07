"""
Receipt document extractor.
Extracts retail receipt/struk data including items, payment method, and merchant info.
"""

import re
from typing import Dict, Any, List, Optional
from ..extractors.base import BaseExtractor, ExtractionResult


class ReceiptExtractor(BaseExtractor):
    """Extracts data from retail receipts/struk/nota."""
    
    def _get_doc_type(self) -> str:
        return 'receipt'
    
    def extract(self, text: str, ocr_regions: Optional[List[Dict]] = None) -> ExtractionResult:
        """Extract receipt data from OCR text."""
        data = {
            'merchant_name': self._extract_merchant_name(text),
            'merchant_address': self._extract_merchant_address(text),
            'receipt_number': self._extract_receipt_number(text),
            'transaction_id': self._extract_transaction_id(text),
            'date': self._extract_date(text),
            'time': self._extract_time(text),
            'cashier_name': self._extract_cashier_name(text),
            'items': self._extract_items(text),
            'subtotal': self._extract_amount(text, 'subtotal'),
            'tax': self._extract_amount(text, 'tax'),
            'discount': self._extract_amount(text, 'discount'),
            'total': self._extract_amount(text, 'total'),
            'payment_method': self._extract_payment_method(text),
            'amount_paid': self._extract_amount(text, 'amount tendered') or self._extract_amount(text, 'cash'),
            'change': self._extract_amount(text, 'change'),
            'currency': self._extract_currency(text),
            'card_number': self._extract_card_number(text),
            'terminal_id': self._extract_terminal_id(text)
        }
        
        # Validate
        validation_errors = self.validate(data)
        
        # Calculate confidence
        filled_fields = sum(1 for v in data.values() if v not in [None, '', [], 0])
        total_fields = len(data)
        confidence = (filled_fields / total_fields * 100) if total_fields > 0 else 0
        
        return ExtractionResult(
            doc_type='receipt',
            data=data,
            confidence=round(confidence, 2),
            validation_errors=validation_errors,
            raw_text=text
        )
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate receipt data consistency."""
        errors = []
        
        # Total should be positive
        if data['total'] and data['total'] <= 0:
            errors.append("Total amount is zero or negative")
        
        # Change should not be negative
        if data['change'] and data['change'] < 0:
            errors.append("Change amount is negative")
        
        # If cash payment, amount paid should >= total
        if data['amount_paid'] and data['total']:
            if data['amount_paid'] < data['total']:
                errors.append("Amount paid less than total")
        
        return errors
    
    def _extract_merchant_name(self, text: str) -> Optional[str]:
        """Extract merchant/store name."""
        patterns = [
            r'(?:merchant|store|shop)[:\s]+([^\n]+)',
            r'^([A-Z][A-Za-z\s&,.]{3,50})\n',
            r'(?:thank you for shopping at|welcome to)\s+([^\n]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_merchant_address(self, text: str) -> Optional[str]:
        """Extract merchant address."""
        patterns = [
            r'(?:address|addr|location)[:\s]+([^\n]+)',
            r'(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Blvd|Jalan|Jl)[^\n]*)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_receipt_number(self, text: str) -> Optional[str]:
        """Extract receipt number."""
        patterns = [
            r'(?:receipt\s*(?:no|number|#))[:\s]*([A-Za-z0-9\-\/]+)',
            r'(?:nota\s*no|struk\s*no)[:\s]*([A-Za-z0-9\-\/]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_transaction_id(self, text: str) -> Optional[str]:
        """Extract transaction ID."""
        patterns = [
            r'(?:transaction\s*(?:id|no))[:\s]*([A-Za-z0-9\-\/]+)',
            r'(?:txn\s*id|trx\s*no)[:\s]*([A-Za-z0-9\-\/]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract receipt date."""
        patterns = [
            r'(?:date|tanggal)[:\s]*(\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
            r'(?:date|tanggal)[:\s]*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_time(self, text: str) -> Optional[str]:
        """Extract transaction time."""
        patterns = [
            r'(?:time|waktu)[:\s]*(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_cashier_name(self, text: str) -> Optional[str]:
        """Extract cashier name/ID."""
        patterns = [
            r'(?:cashier|kasir)[:\s]+([^\n]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract purchased items."""
        items = []
        patterns = [
            r'([^\n]+?)\s+([\d,]+)\s+x\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)',
            r'(\d+)\s+x\s+([^\n@]+?)\s+[@:]\s*([\d,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match) == 4:
                        qty = int(match[0].replace(',', ''))
                        desc = match[1].strip()
                        price = float(match[2].replace(',', ''))
                        amount = float(match[3].replace(',', ''))
                    else:
                        qty = int(match[0])
                        desc = match[1].strip()
                        price = float(match[2].replace(',', ''))
                        amount = qty * price
                    
                    items.append({
                        'quantity': qty,
                        'description': desc,
                        'unit_price': price,
                        'amount': amount
                    })
                except (ValueError, IndexError):
                    continue
            
            if items:
                break
        
        return items
    
    def _extract_amount(self, text: str, label: str) -> Optional[float]:
        """Extract monetary amount."""
        patterns = [
            rf'{label}\s*[:;]?\s*[\$RpIDR]*\s*([\d,]+\.?\d*)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                try:
                    return float(match.replace(',', ''))
                except ValueError:
                    continue
        return None
    
    def _extract_payment_method(self, text: str) -> Optional[str]:
        """Extract payment method."""
        methods = ['cash', 'card', 'credit card', 'debit card', 'tunai', 'kartu kredit', 'kartu debit', 'qris', 'ewallet']
        text_lower = text.lower()
        
        for method in methods:
            if method in text_lower:
                return method.upper()
        
        return None
    
    def _extract_currency(self, text: str) -> Optional[str]:
        """Detect currency."""
        currencies = {
            'USD': r'\$',
            'EUR': r'€',
            'GBP': r'£',
            'IDR': r'Rp|IDR',
        }
        for currency, pattern in currencies.items():
            if re.search(pattern, text):
                return currency
        return 'IDR' if any(kw in text.lower() for kw in ['rupiah', 'rp']) else None
    
    def _extract_card_number(self, text: str) -> Optional[str]:
        """Extract card number (last 4 digits)."""
        patterns = [
            r'card\s*no[:\s]*[\*x]+(\d{4})',
            r'card\s*ending[:\s]*(\d{4})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_terminal_id(self, text: str) -> Optional[str]:
        """Extract terminal/merchant ID."""
        patterns = [
            r'(?:terminal|merchant)\s*id[:\s]*([A-Za-z0-9]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
