# OCR AI - Finance Document Extraction

AI-powered OCR with canonical document representation and multi-format rendering.

## 🏗️ Architecture

```
OCR Engine
    ↓
Canonical Document (blocks, fields, tables)
    ↓
├── render_json()      → Structured JSON
├── render_full_text() → Plain text with structure
└── render_markdown()  → Structure-aware Markdown
```

### Design Principles

1. **Extract Once** - OCR runs once, builds canonical `Document` object
2. **Render Multiple** - Same document renders to JSON, Markdown, Full Text
3. **Structure-Aware** - Markdown detects headings, key-value pairs, tables, paragraphs

## 🎯 Features

### Document Types
- 📄 Invoices
- 🧾 Receipts  
- 🏦 Payment Slips
- 📋 Tax Invoices (Faktur Pajak)
- 💼 Reimbursements

### Output Formats
- **JSON** - Full structured data with blocks, fields, tables
- **Markdown** - Structure-aware with headings, key-value lists, tables
- **Full Text** - Plain text preserving document structure

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Server: `http://localhost:8000`

## 📡 API

### POST /api/ocr/finance
```json
{
  "success": true,
  "doc_type": "receipt",
  "json": { ... },
  "full_text": "...",
  "markdown": "...",
  "fields": [...],
  "blocks": [...]
}
```

## 📦 Structure

```
ocr_engine/
├── document.py          # Canonical Document, Block, Table
├── ocr.py               # OCR Engine → builds Document
├── document_classifier.py
├── extractors/          # Finance-specific extractors
└── validators/
```

## License

MIT
