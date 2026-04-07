"""
Document classifier for finance documents.
Determines the type of document: invoice, receipt, payment slip, tax invoice, or reimbursement.
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    """Result of document classification."""
    doc_type: str
    confidence: float
    reasons: List[str]


class DocumentClassifier:
    """Classifies finance documents based on text content and keywords."""
    
    # Document type definitions with keywords
    DOCUMENT_TYPES = {
        'invoice': {
            'keywords': [
                'invoice', 'bill', 'billing', 'statement', 'amount due',
                'payment terms', 'due date', 'invoice number', 'inv no',
                'bill to', 'ship to', 'subtotal', 'balance due'
            ],
            'patterns': [
                r'invoice\s*#', r'invoice\s*no', r'inv[\s\.\-]?no',
                r'amount\s*due', r'payment\s*due', r'total\s*due'
            ]
        },
        'receipt': {
            'keywords': [
                'receipt', 'struk', 'nota', 'proof of purchase', 'cashier',
                'thank you for shopping', 'change', 'cash', 'card payment',
                'terminal id', 'merchant', 'tunai', 'kembalian', 'pembayaran'
            ],
            'patterns': [
                r'receipt\s*#', r'receipt\s*no', r'transaction\s*id',
                r'terminal\s*id', r'merchant\s*id', r'card\s*no',
                r'total\s*rupiah', r'total\s*payment', r'amount\s*tendered'
            ]
        },
        'payment_slip': {
            'keywords': [
                'payment slip', 'transfer', 'bank transfer', 'wire transfer',
                'remittance', 'payment proof', 'bukti transfer', 'bukti bayar',
                'account number', 'routing number', 'swift code', 'bank name',
                'payer', 'payee', 'beneficiary', 'sender', 'receiver'
            ],
            'patterns': [
                r'bank\s*transfer', r'wire\s*transfer', r'payment\s*slip',
                r'bukti\s*transfer', r'bukti\s*pembayaran', r'account\s*no',
                r'rekening\s*tujuan', r'jumlah\s*transfer', r'transfer\s*amount'
            ]
        },
        'tax_invoice': {
            'keywords': [
                'faktur', 'faktur pajak', 'tax invoice', 'npwp', 'tax number',
                'vat', 'value added tax', 'ppn', 'pajak', 'taxable',
                'tax rate', 'ppn 11', 'dpp', 'dasar pengenaan pajak'
            ],
            'patterns': [
                r'faktur\s*pajak', r'tax\s*invoice', r'npwp\s*no',
                r'npwp\s*:', r'ppn\s*\d+%', r'dpp',
                r'nomor\s*faktur', r'kode\s*faktur'
            ]
        },
        'reimbursement': {
            'keywords': [
                'reimbursement', 'expense report', 'claim', 'expense claim',
                'employee name', 'employee id', 'department', 'manager approval',
                'expense category', 'travel expense', 'meal expense',
                'laporan biaya', 'klaim', 'penggantian', 'perjalanan dinas'
            ],
            'patterns': [
                r'reimbursement\s*form', r'expense\s*report', r'claim\s*#',
                r'employee\s*(id|name|number)', r'manager\s*approval',
                r'expense\s*category', r'laporan\s*biaya',
                r'penggantian\s*biaya', r'perjalanan\s*dinas'
            ]
        }
    }
    
    def classify(self, text: str) -> ClassificationResult:
        """
        Classify document type based on text content.
        
        Args:
            text: Extracted text from document
            
        Returns:
            ClassificationResult with doc_type, confidence, and reasons
        """
        if not text or not text.strip():
            return ClassificationResult(
                doc_type='unknown',
                confidence=0.0,
                reasons=['No text content']
            )
        
        text_lower = text.lower()
        scores: Dict[str, Tuple[int, int, List[str]]] = {}
        
        # Score each document type
        for doc_type, config in self.DOCUMENT_TYPES.items():
            keyword_count = 0
            pattern_count = 0
            matched_reasons = []
            
            # Count keyword matches
            for keyword in config['keywords']:
                if keyword.lower() in text_lower:
                    keyword_count += 1
                    matched_reasons.append(f"Keyword: '{keyword}'")
            
            # Count pattern matches
            for pattern in config['patterns']:
                if re.search(pattern, text_lower):
                    pattern_count += 2  # Patterns weighted higher
                    matched_reasons.append(f"Pattern: '{pattern}'")
            
            # Total score (pattern matches weighted more)
            total_score = keyword_count + pattern_count
            scores[doc_type] = (total_score, keyword_count + pattern_count, matched_reasons)
        
        # Find best match
        best_type = max(scores.items(), key=lambda x: x[1][0])
        doc_type = best_type[0]
        total_score = best_type[1][0]
        max_possible = max(len(config['keywords']) + len(config['patterns']) 
                          for config in self.DOCUMENT_TYPES.values())
        
        # Calculate confidence
        confidence = min(total_score / max_possible * 100, 100)
        
        # Minimum threshold
        if confidence < 15:
            return ClassificationResult(
                doc_type='unknown',
                confidence=confidence,
                reasons=['Insufficient matching patterns']
            )
        
        return ClassificationResult(
            doc_type=doc_type,
            confidence=round(confidence, 2),
            reasons=best_type[1][2][:5]  # Top 5 reasons
        )
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported document types."""
        return list(self.DOCUMENT_TYPES.keys())


# Default instance
classifier = DocumentClassifier()
