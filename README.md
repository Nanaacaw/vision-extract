# OCR AI - Finance Document Extraction

AI-powered finance document OCR with automatic detection and structured data extraction.

## 🎯 Features

### Auto-Detect Finance Documents
Automatically classifies and extracts data from:
- 📄 **Invoices** - Vendor invoices with line items, amounts, tax
- 🧾 **Receipts** - Retail receipts/struk/nota with items and payment info
- 🏦 **Payment Slips** - Bank transfer proofs/bukti transfer
- 📋 **Tax Invoices** - Indonesian Faktur Pajak with NPWP, PPN, DPP
- 💼 **Reimbursements** - Employee expense claims

### Key Capabilities
- ✅ PDF & Image support
- ✅ Automatic document type classification
- ✅ Structured data extraction
- ✅ Data validation (amounts, tax calculations, NPWP format)
- ✅ Confidence scoring
- ✅ Multi-language (English, Indonesian)

## 🏗️ Architecture (KISS + Separation of Concerns)

```
ocr_engine/
├── ocr.py                      # Core OCR engine (PaddleOCR)
├── document_classifier.py      # Document type detection
├── extractors/                 # Finance-specific extractors
│   ├── base.py                # Abstract base interface
│   ├── invoice.py             # Vendor invoices
│   ├── receipt.py             # Retail receipts
│   ├── payment_slip.py        # Payment slips
│   ├── tax_invoice.py         # Tax invoices (Faktur)
│   └── reimbursement.py       # Reimbursement claims
└── validators/
    └── finance.py             # Data validation logic
```

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python main.py
```

Server runs on: `http://localhost:8000`

## 📡 API Endpoints

### 1. Finance Auto-Detection (Recommended)
```bash
POST /api/ocr/finance
```

**Upload any finance document** - automatically detects type and extracts relevant data.

**Response Example (Invoice):**
```json
{
  "success": true,
  "doc_type": "invoice",
  "classification_confidence": 85.5,
  "extraction_confidence": 92.3,
  "data": {
    "vendor_name": "PT Supplier Indonesia",
    "invoice_number": "INV-2024-001",
    "invoice_date": "15/01/2024",
    "total": 1500000.00,
    "subtotal": 1351351.35,
    "tax": 148648.65,
    "currency": "IDR"
  },
  "validation_errors": {},
  "filename": "invoice.pdf"
}
```

**Response Example (Tax Invoice):**
```json
{
  "success": true,
  "doc_type": "tax_invoice",
  "data": {
    "faktur_number": "010.000-24.123456789",
    "npwp_seller": "12.345.678.9-012.345",
    "dpp": 1000000.00,
    "ppn_amount": 110000.00,
    "tax_rate": 11,
    "total_with_tax": 1110000.00
  }
}
```

### 2. Standard OCR
```bash
POST /api/ocr
```
Full text extraction (fallback for non-finance documents).

### 3. Detailed OCR with Regions
```bash
POST /api/ocr/json
```
Returns text with bounding boxes and confidence scores.

### 4. Health Check
```bash
GET /api/health
```

## 📊 Extracted Data by Document Type

### Invoice
- Vendor name & address
- Invoice number & date
- Due date & payment terms
- Bill to / Ship to
- Subtotal, tax, discount, total
- Line items (qty, description, price)
- PO number

### Receipt
- Merchant name & address
- Receipt number & transaction ID
- Date & time
- Items purchased
- Total, payment method, change
- Card number (last 4 digits)

### Payment Slip
- Bank name
- Transfer date & time
- Payer & payee (name + account)
- Transfer amount
- Reference number
- Transfer type (online, RTGS, etc.)
- Status

### Tax Invoice (Faktur Pajak)
- Faktur number
- NPWP (seller & buyer)
- Seller & buyer details
- DPP (Taxable base)
- PPN amount & rate
- Total with tax
- Goods/services list

### Reimbursement
- Employee name & ID
- Department
- Claim number & date
- Expense type & date
- Amount & currency
- Approval status
- Payment status
- Receipt count

## ✅ Validation Rules

The system automatically validates:
- **Amounts**: Total = Subtotal + Tax - Discount
- **NPWP**: 15-digit format (XX.XXX.XXX.X-XXX.XXX)
- **Tax Calculation**: DPP × Rate = PPN
- **Dates**: Valid date formats
- **Bank Accounts**: 8-15 digit format
- **Currency**: Supported currency codes

## 🎨 UI Features

- **Drag & Drop** - Upload files easily
- **Auto-Detection** - Shows detected document type
- **Data Grid** - Clean display of extracted fields
- **Validation Warnings** - Highlights data inconsistencies
- **Multi-format** - Images (PNG, JPG) + PDFs

## 🔧 Configuration

```python
# In ocr_engine/ocr.py
ocr_engine = OCREngine(
    language='en',              # 'en' or other supported langs
    use_angle_cls=True,         # Detect rotated text
    use_gpu=False,              # GPU acceleration
    enable_finance_extraction=True,  # Auto-detect finance docs
    enable_smart_extraction=True     # Smart filtering
)
```

## 📝 Examples

### Extract Invoice
```python
import requests

with open('invoice.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/ocr/finance',
        files={'file': f}
    )
    result = response.json()
    print(f"Document Type: {result['doc_type']}")
    print(f"Total Amount: {result['data']['total']}")
```

### Extract Receipt
```bash
curl -X POST http://localhost:8000/api/ocr/finance \
  -F "file=@receipt.jpg"
```

## 🎯 Performance Tips

1. **Image Quality**: 300 DPI minimum for best results
2. **PDF vs Image**: PDFs maintain quality better
3. **Preprocessing**: Enable for low-quality scans
4. **GPU**: Set `use_gpu=True` for faster processing

## 🛠️ Extending

Add new document types:
1. Create extractor in `ocr_engine/extractors/`
2. Inherit from `BaseExtractor`
3. Add to classifier's `DOCUMENT_TYPES`
4. Register in `ocr_engine/ocr.py`

## 📦 Dependencies

- **PaddleOCR** - OCR engine
- **PyMuPDF** - PDF processing
- **FastAPI** - Web framework
- **OpenCV** - Image preprocessing

## 🐛 Troubleshooting

**Issue**: Document not detected as finance
- **Solution**: Ensure document has clear text keywords

**Issue**: Low confidence scores
- **Solution**: Increase image quality/DPI

**Issue**: Validation errors
- **Solution**: Check if amounts add up correctly in source document

## 📄 License

MIT License

## 🤝 Contributing

Contributions welcome! Please submit PRs for:
- New document type extractors
- Improved regex patterns
- Additional validation rules
- UI enhancements
