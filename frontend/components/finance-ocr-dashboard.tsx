"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Loader2,
  LockKeyhole,
  RotateCcw,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";

import { ConfidenceBar } from "@/components/confidence-bar";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs } from "@/components/ui/tabs";
import type { HealthResponse, OcrResponse } from "@/types/ocr";
import { cn } from "@/lib/utils";

const tabs = ["Full text", "Fields", "Blocks"];

function formatFileSize(size: number) {
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(2)} MB`;
}

function normalizeDocType(docType?: string) {
  if (!docType || docType === "unknown") {
    return "Needs review";
  }
  return docType.replaceAll("_", " ");
}

export function FinanceOcrDashboard() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preprocess, setPreprocess] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OcrResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [activeTab, setActiveTab] = useState(tabs[0]);

  useEffect(() => {
    fetch("/api/backend-health")
      .then((response) => response.json())
      .then((payload: HealthResponse) => setHealth(payload))
      .catch(() => setHealth({ status: "unreachable", engine: "PaddleOCR PP-OCRv5" } as HealthResponse));
  }, []);

  useEffect(() => {
    if (!isProcessing) {
      return;
    }

    setProgress(16);
    const timer = window.setInterval(() => {
      setProgress((current) => Math.min(current + 8, 92));
    }, 450);

    return () => window.clearInterval(timer);
  }, [isProcessing]);

  const lowConfidenceCount = useMemo(() => {
    if (!result) {
      return 0;
    }
    return result.blocks.filter((block) => block.confidence < 0.75).length;
  }, [result]);

  function selectFile(nextFile?: File) {
    if (!nextFile) {
      return;
    }
    setFile(nextFile);
    setError(null);
    setResult(null);
    setProgress(0);
  }

  async function processDocument() {
    if (!file) {
      setError("Choose a document before processing.");
      return;
    }

    setIsProcessing(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("preprocess", String(preprocess));

    try {
      const response = await fetch("/api/ocr/finance", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail ?? "OCR processing failed.");
      }

      setResult(payload as OcrResponse);
      setActiveTab(tabs[0]);
      setProgress(100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "OCR processing failed.");
      setProgress(0);
    } finally {
      setIsProcessing(false);
    }
  }

  function reset() {
    setFile(null);
    setResult(null);
    setError(null);
    setProgress(0);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  return (
    <main className="min-h-dvh">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-4 border-b pb-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge variant="outline">Internal Finance Ops</Badge>
              <Badge variant={health?.status === "healthy" ? "secondary" : "warning"}>
                {health?.status === "healthy" ? "Backend online" : "Backend check"}
              </Badge>
            </div>
            <h1 className="text-2xl font-semibold tracking-normal sm:text-3xl">Finance OCR Review</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              Process sensitive finance documents locally through the FastAPI OCR backend, then review
              extracted text, confidence, and structured fields before using the data.
            </p>
          </div>
          <div className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-3 lg:min-w-[520px]">
            <div className="rounded-md border bg-card p-3">
              <ShieldCheck className="mb-2 h-4 w-4 text-secondary" aria-hidden="true" />
              <div className="font-medium text-foreground">PP-OCRv5</div>
              <div className="truncate">{health?.ocr_recognition_model ?? "PP-OCRv5_mobile_rec"}</div>
            </div>
            <div className="rounded-md border bg-card p-3">
              <LockKeyhole className="mb-2 h-4 w-4 text-secondary" aria-hidden="true" />
              <div className="font-medium text-foreground">Local proxy</div>
              <div>No direct browser backend URL</div>
            </div>
            <div className="rounded-md border bg-card p-3">
              <FileText className="mb-2 h-4 w-4 text-secondary" aria-hidden="true" />
              <div className="font-medium text-foreground">PDF DPI</div>
              <div>{health?.pdf_dpi ?? 150}</div>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[380px_1fr]">
          <Card className="h-fit">
            <CardHeader>
              <CardTitle>Upload Document</CardTitle>
              <CardDescription>Images and PDFs are forwarded to the backend OCR service.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(event) => {
                  event.preventDefault();
                  setIsDragging(false);
                  selectFile(event.dataTransfer.files[0]);
                }}
                className={cn(
                  "flex min-h-48 w-full cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed bg-muted/35 px-4 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  isDragging && "border-secondary bg-secondary/10",
                )}
              >
                <UploadCloud className="mb-3 h-8 w-8 text-secondary" aria-hidden="true" />
                <span className="font-medium">Drop a document here</span>
                <span className="mt-1 text-sm text-muted-foreground">PNG, JPG, WEBP, TIFF, BMP, or PDF</span>
              </button>

              <Input
                ref={inputRef}
                type="file"
                accept=".png,.jpg,.jpeg,.webp,.tif,.tiff,.bmp,.pdf"
                className="sr-only"
                onChange={(event) => selectFile(event.target.files?.[0])}
              />

              {file ? (
                <div className="rounded-md border bg-card p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{file.name}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{formatFileSize(file.size)}</div>
                    </div>
                    <Button type="button" variant="ghost" size="sm" onClick={reset}>
                      <RotateCcw className="h-4 w-4" aria-hidden="true" />
                      Reset
                    </Button>
                  </div>
                </div>
              ) : null}

              <label className="flex min-h-11 items-center gap-3 rounded-md border bg-card px-3 text-sm">
                <input
                  type="checkbox"
                  checked={preprocess}
                  onChange={(event) => setPreprocess(event.target.checked)}
                  className="h-4 w-4 rounded border-input accent-primary"
                />
                Use image preprocessing
              </label>

              {isProcessing ? (
                <div className="space-y-2">
                  <Progress value={progress} />
                  <div className="text-xs text-muted-foreground">Processing OCR and finance extraction...</div>
                </div>
              ) : null}

              {error ? (
                <div className="flex gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>{error}</span>
                </div>
              ) : null}

              <Button type="button" className="w-full" disabled={!file || isProcessing} onClick={processDocument}>
                {isProcessing ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                Process OCR
              </Button>
            </CardContent>
          </Card>

          <div className="space-y-6">
            {result ? (
              <>
                <div className="grid gap-4 md:grid-cols-4">
                  <Card>
                    <CardHeader>
                      <CardDescription>Document type</CardDescription>
                      <CardTitle className="capitalize">{normalizeDocType(result.doc_type)}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardDescription>Classification</CardDescription>
                      <CardTitle>{Math.round(result.classification_confidence)}%</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardDescription>Pages</CardDescription>
                      <CardTitle>{result.page_count}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardDescription>Processing</CardDescription>
                      <CardTitle>{result.processing_time}s</CardTitle>
                    </CardHeader>
                  </Card>
                </div>

                <Card>
                  <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <CardTitle>Review Workspace</CardTitle>
                      <CardDescription>
                        {result.blocks.length} OCR blocks, {result.fields.length} extracted fields,
                        {lowConfidenceCount} low-confidence blocks.
                      </CardDescription>
                    </div>
                    <Tabs tabs={tabs} value={activeTab} onValueChange={setActiveTab} />
                  </CardHeader>
                  <CardContent>
                    {activeTab === "Full text" ? (
                      <pre className="max-h-[560px] overflow-auto rounded-md border bg-muted/40 p-4 text-sm leading-6 whitespace-pre-wrap">
                        {result.full_text || "No text detected"}
                      </pre>
                    ) : null}

                    {activeTab === "Fields" ? (
                      <div className="overflow-hidden rounded-md border">
                        {result.fields.length ? (
                          <table className="w-full text-left text-sm">
                            <thead className="bg-muted text-xs uppercase text-muted-foreground">
                              <tr>
                                <th className="px-4 py-3 font-medium">Field</th>
                                <th className="px-4 py-3 font-medium">Value</th>
                                <th className="px-4 py-3 font-medium">Confidence</th>
                              </tr>
                            </thead>
                            <tbody>
                              {result.fields.map((field) => (
                                <tr key={`${field.name}-${field.value}`} className="border-t">
                                  <td className="px-4 py-3 font-medium">{field.name}</td>
                                  <td className="px-4 py-3">{field.value}</td>
                                  <td className="px-4 py-3">
                                    <ConfidenceBar value={field.confidence} />
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <div className="flex min-h-40 items-center justify-center text-sm text-muted-foreground">
                            No structured fields were extracted.
                          </div>
                        )}
                      </div>
                    ) : null}

                    {activeTab === "Blocks" ? (
                      <div className="max-h-[560px] overflow-auto rounded-md border">
                        {result.blocks.map((block, index) => (
                          <div key={`${block.page}-${index}`} className="grid gap-3 border-b p-4 last:border-b-0 md:grid-cols-[1fr_160px_90px]">
                            <div>
                              <div className="text-sm font-medium">{block.text}</div>
                              <div className="mt-1 text-xs text-muted-foreground">
                                Page {block.page} · {block.type} · x{block.bbox.x} y{block.bbox.y}
                              </div>
                            </div>
                            <ConfidenceBar value={block.confidence} />
                            <Badge variant={block.confidence >= 0.75 ? "muted" : "warning"}>
                              {block.confidence >= 0.75 ? "Review" : "Check"}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </CardContent>
                </Card>

                <div className="flex items-center gap-2 rounded-lg border bg-card p-4 text-sm text-muted-foreground">
                  <CheckCircle2 className="h-4 w-4 text-secondary" aria-hidden="true" />
                  OCR output is ready for human review. Validate totals, dates, tax IDs, and account references before export.
                </div>
              </>
            ) : (
              <EmptyState />
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
