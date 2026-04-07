"""
Finance data validation module.
Validates extracted finance data for consistency and accuracy.
"""

import re
from typing import Dict, Any, List
from datetime import datetime


class FinanceValidator:
    """Validates finance document extracted data."""
    
    @staticmethod
    def validate_amount(amount: Any, positive_only: bool = True) -> List[str]:
        """Validate amount value."""
        errors = []
        if amount is None:
            return errors
        
        try:
            val = float(amount)
            if positive_only and val < 0:
                errors.append(f"Amount should be positive: {amount}")
        except (ValueError, TypeError):
            errors.append(f"Invalid amount format: {amount}")
        
        return errors
    
    @staticmethod
    def validate_date(date_str: Any) -> List[str]:
        """Validate date format."""
        errors = []
        if date_str is None:
            return errors
        
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%m-%d-%Y',
            '%Y/%m/%d', '%Y-%m-%d', '%d/%m/%y', '%d-%m-%y'
        ]
        
        valid = False
        for fmt in date_formats:
            try:
                datetime.strptime(str(date_str), fmt)
                valid = True
                break
            except ValueError:
                continue
        
        if not valid:
            errors.append(f"Invalid date format: {date_str}")
        
        return errors
    
    @staticmethod
    def validate_npwp(npwp: str) -> List[str]:
        """Validate Indonesian NPWP format (15 digits)."""
        errors = []
        if npwp is None:
            return errors
        
        # Remove formatting
        clean = re.sub(r'[.\-\s]', '', npwp)
        
        if not re.match(r'^\d{15}$', clean):
            errors.append(f"Invalid NPWP format (should be 15 digits): {npwp}")
        
        return errors
    
    @staticmethod
    def validate_tax_calculation(dpp: float, tax_rate: float, tax_amount: float, tolerance: float = 1.0) -> List[str]:
        """Validate tax calculation: DPP * rate = tax_amount."""
        errors = []
        
        expected_tax = dpp * (tax_rate / 100)
        if abs(expected_tax - tax_amount) > tolerance:
            errors.append(
                f"Tax calculation mismatch: DPP {dpp} × {tax_rate}% = {expected_tax}, "
                f"but got {tax_amount}"
            )
        
        return errors
    
    @staticmethod
    def validate_total(subtotal: float, additions: List[float], deductions: List[float], 
                      total: float, tolerance: float = 1.0) -> List[str]:
        """Validate total calculation: subtotal + additions - deductions = total."""
        errors = []
        
        expected_total = subtotal + sum(additions) - sum(deductions)
        if abs(expected_total - total) > tolerance:
            errors.append(
                f"Total calculation mismatch: {subtotal} + {sum(additions)} - "
                f"{sum(deductions)} = {expected_total}, but got {total}"
            )
        
        return errors
    
    @staticmethod
    def validate_invoice_number(invoice_no: str) -> List[str]:
        """Validate invoice number format."""
        errors = []
        if not invoice_no or not invoice_no.strip():
            errors.append("Invoice number is empty")
        elif len(invoice_no.strip()) < 3:
            errors.append(f"Invoice number too short: {invoice_no}")
        
        return errors
    
    @staticmethod
    def validate_bank_account(account: str) -> List[str]:
        """Validate bank account number."""
        errors = []
        if account is None:
            return errors
        
        clean = re.sub(r'[\-\s]', '', account)
        if not re.match(r'^\d{8,15}$', clean):
            errors.append(f"Invalid bank account format (should be 8-15 digits): {account}")
        
        return errors
    
    @staticmethod
    def validate_currency(currency: str) -> List[str]:
        """Validate currency code."""
        errors = []
        valid_currencies = ['USD', 'EUR', 'GBP', 'IDR', 'JPY', 'AUD', 'SGD', 'CNY']
        
        if currency and currency.upper() not in valid_currencies:
            errors.append(f"Unsupported currency: {currency}")
        
        return errors
    
    @classmethod
    def validate_document(cls, doc_type: str, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Comprehensive validation for finance document.
        Returns dict of field -> errors.
        """
        all_errors = {}
        
        if doc_type == 'invoice':
            all_errors['invoice_number'] = cls.validate_invoice_number(data.get('invoice_number', ''))
            if data.get('invoice_date'):
                all_errors['invoice_date'] = cls.validate_date(data['invoice_date'])
            if data.get('total'):
                all_errors['total'] = cls.validate_amount(data['total'])
            if data.get('subtotal') and data.get('tax') and data.get('tax_rate'):
                all_errors['tax_calc'] = cls.validate_tax_calculation(
                    data['subtotal'], data['tax_rate'], data['tax']
                )
        
        elif doc_type == 'receipt':
            if data.get('total'):
                all_errors['total'] = cls.validate_amount(data['total'])
            if data.get('date'):
                all_errors['date'] = cls.validate_date(data['date'])
        
        elif doc_type == 'payment_slip':
            if data.get('amount'):
                all_errors['amount'] = cls.validate_amount(data['amount'])
            if data.get('transfer_date'):
                all_errors['transfer_date'] = cls.validate_date(data['transfer_date'])
            if data.get('payer_account'):
                all_errors['payer_account'] = cls.validate_bank_account(data['payer_account'])
            if data.get('payee_account'):
                all_errors['payee_account'] = cls.validate_bank_account(data['payee_account'])
        
        elif doc_type == 'tax_invoice':
            if data.get('npwp_seller'):
                all_errors['npwp_seller'] = cls.validate_npwp(data['npwp_seller'])
            if data.get('dpp') and data.get('tax_rate') and data.get('ppn_amount'):
                all_errors['tax_calc'] = cls.validate_tax_calculation(
                    data['dpp'], data['tax_rate'], data['ppn_amount']
                )
            if data.get('total_with_tax'):
                all_errors['total_with_tax'] = cls.validate_amount(data['total_with_tax'])
        
        elif doc_type == 'reimbursement':
            if data.get('amount'):
                all_errors['amount'] = cls.validate_amount(data['amount'])
            if data.get('claim_date'):
                all_errors['claim_date'] = cls.validate_date(data['claim_date'])
            if data.get('expense_date'):
                all_errors['expense_date'] = cls.validate_date(data['expense_date'])
        
        # Remove empty error lists
        return {k: v for k, v in all_errors.items() if v}
