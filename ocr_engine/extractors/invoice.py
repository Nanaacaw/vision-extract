"""
Invoice document extractor.
Extracts vendor invoice data including line items, amounts, and vendor details.
"""

import re
from typing import Dict, Any, List, Optional
from ..extractors.base import BaseExtractor, ExtractionResult


class InvoiceExtractor(BaseExtractor):
    """Extracts data from vendor invoices."""
    
    def _get_doc_type(self) -> str:
        return 'invoice'
    
    def extract(self, text: str, ocr_regions: Optional[List[Dict]] = None) -> ExtractionResult:
        """Extract invoice data from OCR text."""
        data = {
            'vendor_name': self._extract_vendor_name(text),
            'vendor_address': self._extract_vendor_address(text),
            'invoice_number': self._extract_invoice_number(text),
            'invoice_date': self._extract_invoice_date(text),
            'due_date': self._extract_due_date(text),
            'bill_to': self._extract_bill_to(text),
            'ship_to': self._extract_ship_to(text),
            'subtotal': self._extract_amount(text, 'subtotal'),
            'tax': self._extract_amount(text, 'tax'),
            'tax_rate': self._extract_tax_rate(text),
            'discount': self._extract_amount(text, 'discount'),
            'total': self._extract_amount(text, 'total'),
            'amount_due': self._extract_amount(text, 'amount due') or self._extract_amount(text, 'balance due'),
            'currency': self._extract_currency(text),
            'line_items': self._extract_line_items(text),
            'payment_terms': self._extract_payment_terms(text),
            'po_number': self._extract_po_number(text),
            'notes': self._extract_notes(text)
        }
        
        # Validate
        validation_errors = self.validate(data)
        
        # Calculate confidence based on fields found
        filled_fields = sum(1 for v in data.values() if v not in [None, '', [], 0])
        total_fields = len(data)
        confidence = (filled_fields / total_fields * 100) if total_fields > 0 else 0
        
        return ExtractionResult(
            doc_type='invoice',
            data=data,
            confidence=round(confidence, 2),
            validation_errors=validation_errors,
            raw_text=text
        )
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate invoice data consistency."""
        errors = []
        
        # Check if total makes sense
        if data['subtotal'] and data['total']:
            if data['tax'] and data['subtotal'] + data['tax'] > data['total'] * 1.1:
                errors.append(f"Total ({data['total']}) significantly less than subtotal + tax ({data['subtotal'] + data['tax']})")
            elif not data['tax'] and data['subtotal'] > data['total'] * 1.05:
                errors.append(f"Total ({data['total']}) less than subtotal ({data['subtotal']}) without tax")
        
        # Invoice number should exist
        if not data['invoice_number']:
            errors.append("Invoice number not found")
        
        # Date should exist
        if not data['invoice_date']:
            errors.append("Invoice date not found")
        
        # Amount should be positive
        if data['total'] and data['total'] <= 0:
            errors.append(f"Total amount is negative or zero: {data['total']}")
        
        return errors
    
    def _extract_vendor_name(self, text: str) -> Optional[str]:
        """Extract vendor/company name."""
        patterns = [
            r'from[:\s]+([A-Z][A-Za-z\s&,.]+?)(?:\n|$)',
            r'(?:vendor|supplier|billed by)[:\s]+([^\n]+)',
            r'^([A-Z][A-Za-z\s&,.]{3,50})\n',  # First line often company name
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_vendor_address(self, text: str) -> Optional[str]:
        """Extract vendor address."""
        patterns = [
            r'(?:address|addr)[:\s]+([^\n]+)',
            r'(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Blvd|Lane|Ln|Drive|Dr|Court|Ct)[^\n]*)'
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number."""
        patterns = [
            r'(?:invoice\s*(?:no|number|#)|inv\s*no|invoice\s*\#)[:\s]*([A-Za-z0-9\-\/]+)',
            r'(?:bill\s*no|billing\s*ref)[:\s]*([A-Za-z0-9\-\/]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_invoice_date(self, text: str) -> Optional[str]:
        """Extract invoice date."""
        patterns = [
            r'(?:invoice\s*date|date)[:\s]*(\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
            r'(?:invoice\s*date|date)[:\s]*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract payment due date."""
        patterns = [
            r'(?:due\s*date|payment\s*due|pay\s*by)[:\s]*(\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
            r'(?:due\s*date|payment\s*due)[:\s]*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_bill_to(self, text: str) -> Optional[str]:
        """Extract bill to / customer info."""
        patterns = [
            r'(?:bill\s*to|billed\s*to|customer)[:\s]+([^\n]+(?:\n[^\n]+){0,2})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_ship_to(self, text: str) -> Optional[str]:
        """Extract ship to / delivery address."""
        patterns = [
            r'(?:ship\s*to|delivered\s*to|delivery)[:\s]+([^\n]+(?:\n[^\n]+){0,2})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_amount(self, text: str, label: str) -> Optional[float]:
        """Extract monetary amount."""
        patterns = [
            rf'{label}\s*[:;]?\s*[\$RpIDR]*\s*([\d,]+\.?\d*)',
            rf'{label}\s*amount\s*[:;]?\s*[\$RpIDR]*\s*([\d,]+\.?\d*)',
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
            r'(?:tax|vat|ppn)\s*(?:rate)?[:\s]*(\d+)%',
            r'(?:tax|vat|ppn)\s*(\d+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                try:
                    return float(match)
                except ValueError:
                    continue
        return None
    
    def _extract_currency(self, text: str) -> Optional[str]:
        """Detect currency."""
        currencies = {
            'USD': r'\$',
            'EUR': r'€',
            'GBP': r'£',
            'JPY': r'¥',
            'IDR': r'Rp|IDR',
        }
        for currency, pattern in currencies.items():
            if re.search(pattern, text):
                return currency
        return None
    
    def _extract_line_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract line items from invoice."""
        items = []
        # Look for patterns like: Qty x Description @ Price = Amount
        patterns = [
            r'(\d+)\s+x\s+([^\n@]+?)\s+@\s*[\$Rp]*([\d,]+\.?\d*)\s*=\s*[\$Rp]*([\d,]+\.?\d*)',
            r'(\d+)\s+([^\n]+?)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    qty = int(match[0])
                    desc = match[1].strip()
                    price = float(match[2].replace(',', ''))
                    amount = float(match[3].replace(',', ''))
                    
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
    
    def _extract_payment_terms(self, text: str) -> Optional[str]:
        """Extract payment terms."""
        patterns = [
            r'(?:payment\s*terms|terms)[:\s]+([^\n]+)',
            r'(?:net\s*\d+|due\s*on\s*receipt)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_po_number(self, text: str) -> Optional[str]:
        """Extract purchase order number."""
        patterns = [
            r'(?:po\s*no|po\s*number|purchase\s*order)[:\s]*([A-Za-z0-9\-\/]+)',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
    
    def _extract_notes(self, text: str) -> Optional[str]:
        """Extract notes or comments."""
        patterns = [
            r'(?:notes?|comments?|remarks?)[:\s]+([^\n]+(?:\n[^\n]+){0,3})',
        ]
        for pattern in patterns:
            match = self._find_pattern(text, pattern)
            if match:
                return match.strip()
        return None
