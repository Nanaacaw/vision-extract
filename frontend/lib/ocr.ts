export function getBackendUrl() {
  return process.env.OCR_BACKEND_URL ?? "http://localhost:8001";
}
