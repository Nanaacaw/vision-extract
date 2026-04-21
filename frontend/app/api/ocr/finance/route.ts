import { NextResponse } from "next/server";

import { getBackendUrl } from "@/lib/ocr";

export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(request: Request) {
  const formData = await request.formData();
  const response = await fetch(`${getBackendUrl()}/api/ocr/finance`, {
    method: "POST",
    body: formData,
  });

  const payload = await response.text();
  return new NextResponse(payload, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
