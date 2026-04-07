"""
OCR AI - Main Application Entry Point

A web-based OCR application using FastAPI and PaddleOCR.
Supports images, PDFs, and smart data extraction.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routes import router

app = FastAPI(
    title="OCR AI",
    description="AI-powered Optical Character Recognition application with PaddleOCR",
    version="2.0.0"
)

# Include API routes
app.include_router(router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the main HTML page."""
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🚀 Starting OCR AI Application")
    print("=" * 60)
    print("📍 Server: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("=" * 60)
    print("\n✨ Using PaddleOCR Engine")
    print("📄 Supports: Images (PNG, JPG, etc.) + PDF files")
    print("🎯 Features: Smart data extraction, Logo detection")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
