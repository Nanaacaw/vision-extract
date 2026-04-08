"""
Canonical document representation and renderers.
Build once from OCR, render to multiple formats.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re


@dataclass
class Block:
    """A text block with position and semantic type."""
    text: str
    bbox: Dict[str, int]
    confidence: float
    page: int = 1
    block_type: str = "text"
    key: Optional[str] = None
    value: Optional[str] = None


@dataclass
class ExtractedField:
    """A high-confidence extracted field."""
    name: str
    value: str
    confidence: float = 1.0


class Document:
    """
    Canonical document representation.
    Build once from OCR, render to multiple formats.
    """
    
    def __init__(self, doc_type: str = "unknown"):
        self.doc_type = doc_type
        self.blocks: List[Block] = []
        self.fields: List[ExtractedField] = []
        self.page_count: int = 1
        self.classification_confidence: float = 0.0
        self.metadata: Dict[str, Any] = {}
    
    def add_block(self, block: Block):
        self.blocks.append(block)
    
    def add_field(self, field: ExtractedField):
        self.fields.append(field)
    
    def add_blocks_from_ocr(self, words: List[Dict], page: int = 1):
        """Convert OCR words to canonical blocks."""
        if not words:
            return
        
        # Sort by Y position (rows), then X position (columns)
        sorted_words = sorted(words, key=lambda w: (w['bbox']['y'] // 20 * 20, w['bbox']['x']))
        
        for word in sorted_words:
            text = word.get('text', '').strip()
            if not text:
                continue
            
            bbox = word.get('bbox', {})
            confidence = word.get('confidence', 0.5)
            
            block = Block(
                text=text,
                bbox=bbox,
                confidence=confidence,
                page=page,
                block_type=self._detect_block_type(text)
            )
            
            if block.block_type == "key_value":
                kv = self._parse_key_value(text)
                if kv:
                    block.key = kv['key']
                    block.value = kv['value']
            
            self.blocks.append(block)
    
    def _detect_block_type(self, text: str) -> str:
        """Detect semantic type of a text block."""
        headings = [
            'total payment', 'payment method', 'receiver detail', 'transaction detail',
            'sender detail', 'account detail', 'order detail', 'billing detail',
            'shipping detail', 'invoice', 'receipt', 'faktur', 'nota', 'struk',
            'subtotal', 'service charge', 'cashier', 'server', 'dana'
        ]
        lower = text.lower().strip()
        if any(lower == h or lower.startswith(h) for h in headings):
            return "heading"
        
        labels = [
            'payment method', 'dana account', 'transaction id', 'merchant order',
            'remarks', 'name', 'account', 'reference', 'order id', 'phone',
            'email', 'address', 'date', 'time', 'amount', 'total'
        ]
        if any(lower.startswith(label) for label in labels):
            return "key_value"
        
        return "text"
    
    def _parse_key_value(self, text: str) -> Optional[Dict[str, str]]:
        """Parse key-value pair from text."""
        patterns = [
            r'^(.+?)\s{2,}(.+)$',  # Multiple spaces
            r'^(.+?)\s*:\s*(.+)$',  # Colon
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return {'key': match.group(1).strip(), 'value': match.group(2).strip()}
        
        return None
    
    def render_json(self) -> Dict[str, Any]:
        """Render to structured JSON."""
        return {
            'doc_type': self.doc_type,
            'page_count': self.page_count,
            'classification_confidence': self.classification_confidence,
            'fields': [{'name': f.name, 'value': f.value, 'confidence': f.confidence} for f in self.fields],
            'blocks': [
                {
                    'text': b.text,
                    'type': b.block_type,
                    'key': b.key,
                    'value': b.value,
                    'bbox': b.bbox,
                    'confidence': b.confidence,
                    'page': b.page
                }
                for b in self.blocks
            ],
            'metadata': self.metadata
        }
    
    def render_full_text(self) -> str:
        """Render to plain full text (preserving structure)."""
        lines = []
        prev_page = 1
        prev_y = -100
        
        for block in self.blocks:
            if block.page != prev_page:
                lines.append('')
                lines.append(f'--- Page {block.page} ---')
                lines.append('')
                prev_page = block.page
                prev_y = -100
            
            y = block.bbox.get('y', 0) if block.bbox else 0
            
            # Add blank line if significant vertical gap
            if prev_y >= 0 and (y - prev_y) > 25:
                lines.append('')
            
            lines.append(block.text)
            prev_y = y + (block.bbox.get('height', 0) if block.bbox else 0)
        
        return '\n'.join(lines).strip()
    
    def render_markdown(self) -> str:
        """
        Render to clean markdown format.
        - Headers as bold text
        - Key-value as bold key: value
        - Amounts highlighted
        - Regular text as-is
        """
        if not self.blocks:
            return 'No text detected'
        
        md_parts = []
        prev_y = -100
        
        for block in self.blocks:
            y = block.bbox.get('y', 0) if block.bbox else 0
            
            # Add blank line for vertical gaps
            if prev_y >= 0 and (y - prev_y) > 25:
                md_parts.append('')
            
            text = block.text
            
            # Headers (short, uppercase, or known patterns)
            if block.block_type == "heading":
                md_parts.append(f'**{text}**')
            
            # Key-value pairs
            elif block.block_type == "key_value" and block.key and block.value:
                md_parts.append(f'**{block.key}**: {block.value}')
            
            # Amounts (Rp, $, etc.)
            elif re.match(r'^(Rp|IDR|\$|€|£)\s*[\d,.]+', text, re.IGNORECASE):
                md_parts.append(f'**{text}**')
            
            # Status words
            elif text.upper() in ['SUCCESS', 'FAILED', 'PENDING', 'LUNAS', 'PAID']:
                md_parts.append(f'**{text}**')
            
            # Regular text
            else:
                md_parts.append(text)
            
            prev_y = y + (block.bbox.get('height', 0) if block.bbox else 0)
        
        return '\n'.join(md_parts).strip()
