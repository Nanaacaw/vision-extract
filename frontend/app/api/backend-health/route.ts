import { NextResponse } from "next/server";

import { getBackendUrl } from "@/lib/ocr";

export const runtime = "nodejs";

export async function GET() {
  try {
    const response = await fetch(`${getBackendUrl()}/api/health`, {
      cache: "no-store",
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch {
    return NextResponse.json(
      {
        status: "unreachable",
        engine: "PaddleOCR PP-OCRv5",
      },
      { status: 503 },
    );
  }
}
