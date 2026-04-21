"""OCR AI backend application entry point."""

from fastapi import FastAPI
from api.routes import router

app = FastAPI(
    title="OCR AI - Finance",
    description="AI-powered finance document OCR with PaddleOCR",
    version="2.0.0"
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root() -> dict[str, object]:
    """Return backend service metadata."""
    return {
        "service": "OCR AI - Finance Edition",
        "status": "ok",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": ["/api/ocr/finance", "/api/preview", "/api/health"],
    }


if __name__ == "__main__":
    import os
    import uvicorn

    backend_port = int(os.getenv("OCR_BACKEND_PORT", "8001"))

    print("=" * 60)
    print("Starting OCR AI - Finance Edition")
    print("=" * 60)
    print(f"Server: http://localhost:{backend_port}")
    print(f"API Docs: http://localhost:{backend_port}/docs")
    print("=" * 60)
    print("\nUsing PaddleOCR Engine")
    print("Supports: Images + PDF files")
    print("Features: Finance auto-detection, JSON/Markdown/Text rendering")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=backend_port,
        reload=False,
        log_level="info"
    )
