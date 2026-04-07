# OCR AI Project

An AI-powered Optical Character Recognition (OCR) application with a web interface.

## Features

- Extract text from images using Tesseract OCR
- Support for multiple image formats (PNG, JPG, JPEG, BMP, TIFF)
- Image preprocessing for better accuracy
- RESTful API with FastAPI
- Beautiful web interface
- Export extracted text as TXT or JSON

## Prerequisites

- Python 3.8+
- Tesseract OCR installed on your system

## Installation

### 1. Install Tesseract OCR

**Windows:**
- Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
- Run the installer (default path: `C:\Program Files\Tesseract-OCR`)
- Add Tesseract to your PATH environment variable

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

### 2. Setup Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Start the Server

```bash
python main.py
```

The application will start at: http://localhost:8000

### API Endpoints

- `POST /api/ocr` - Extract text from an uploaded image
- `POST /api/ocr/json` - Extract text with detailed information (confidence, bounding boxes)
- `GET /api/health` - Health check endpoint

### Example API Usage

```bash
# Extract text from image
curl -X POST -F "file=@image.png" http://localhost:8000/api/ocr

# Get detailed OCR results
curl -X POST -F "file=@image.png" http://localhost:8000/api/ocr/json
```

## Project Structure

```
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── ocr_engine/         # OCR engine module
│   ├── __init__.py
│   ├── ocr.py          # Core OCR functionality
│   └── preprocessing.py # Image preprocessing
├── api/                # API routes
│   ├── __init__.py
│   └── routes.py
└── static/             # Frontend files
    ├── index.html
    ├── style.css
    └── script.js
```

## Technologies Used

- **Backend:** FastAPI (Python)
- **OCR Engine:** Tesseract via pytesseract
- **Image Processing:** OpenCV, Pillow
- **Frontend:** HTML5, CSS3, JavaScript
