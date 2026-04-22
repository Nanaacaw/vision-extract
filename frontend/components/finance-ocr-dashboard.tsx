"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  Crop,
  FileText,
  ImageIcon,
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
import { cn } from "@/lib/utils";
import type { HealthResponse, OcrBlock, OcrResponse } from "@/types/ocr";

const tabs = ["Blocks", "Words", "Fields", "Full text"];
const preprocessProfiles = [
  { value: "auto", label: "Auto" },
  { value: "receipt", label: "Receipt" },
  { value: "camera", label: "Camera" },
  { value: "clean", label: "Clean scan" },
  { value: "none", label: "None" },
];

type BatchItem = {
  id: string;
  file: File;
  status: "queued" | "processing" | "done" | "error";
  result?: OcrResponse;
  error?: string;
};

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
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [filePreviewUrl, setFilePreviewUrl] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [preprocess, setPreprocess] = useState(true);
  const [preprocessProfile, setPreprocessProfile] = useState("auto");
  const [smartCrop, setSmartCrop] = useState(false);
  const [batchItems, setBatchItems] = useState<BatchItem[]>([]);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OcrResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [activeTab, setActiveTab] = useState(tabs[0]);
  const [selectedBlockIndex, setSelectedBlockIndex] = useState(0);

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

  useEffect(() => {
    if (!file) {
      setFilePreviewUrl(null);
      setImageSize({ width: 0, height: 0 });
      return;
    }

    const url = URL.createObjectURL(file);
    setFilePreviewUrl(url);
    setImageSize({ width: 0, height: 0 });

    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (videoRef.current && cameraStream) {
      videoRef.current.srcObject = cameraStream;
    }
  }, [cameraStream]);

  useEffect(() => {
    return () => {
      cameraStream?.getTracks().forEach((track) => track.stop());
    };
  }, [cameraStream]);

  const lowConfidenceCount = useMemo(() => {
    if (!result) {
      return 0;
    }
    return result.blocks.filter((block) => block.confidence < 0.75).length;
  }, [result]);

  const completedBatchCount = useMemo(
    () => batchItems.filter((item) => item.status === "done" || item.status === "error").length,
    [batchItems],
  );

  const selectedBlock = result?.blocks[selectedBlockIndex] ?? null;
  const isPdfPreview = Boolean(file?.type === "application/pdf" || file?.name.toLowerCase().endsWith(".pdf"));
  const isImagePreview = Boolean(filePreviewUrl && file && !isPdfPreview);

  function selectFile(nextFile?: File, nextProfile?: string, clearBatch = true) {
    if (!nextFile) {
      return;
    }
    if (clearBatch) {
      setBatchItems([]);
      setActiveBatchId(null);
    }
    setFile(nextFile);
    setError(null);
    setCameraError(null);
    setResult(null);
    setProgress(0);
    setSelectedBlockIndex(0);
    if (nextProfile) {
      setPreprocess(true);
      setPreprocessProfile(nextProfile);
    }
    stopCamera();
  }

  function selectFiles(nextFiles?: FileList | File[] | null) {
    const files = Array.from(nextFiles ?? []).filter(Boolean);
    if (!files.length) {
      return;
    }

    if (files.length === 1) {
      selectFile(files[0]);
      return;
    }

    const items = files.map((nextFile, index) => ({
      id: `${nextFile.name}-${nextFile.size}-${nextFile.lastModified}-${index}`,
      file: nextFile,
      status: "queued" as const,
    }));
    setBatchItems(items);
    setActiveBatchId(items[0].id);
    selectFile(items[0].file, undefined, false);
  }

  function openBatchItem(item: BatchItem) {
    setActiveBatchId(item.id);
    setFile(item.file);
    setError(item.error ?? null);
    setResult(item.result ?? null);
    setSelectedBlockIndex(0);
    setActiveTab(tabs[0]);
  }

  function stopCamera() {
    cameraStream?.getTracks().forEach((track) => track.stop());
    setCameraStream(null);
  }

  async function startCamera() {
    setCameraError(null);

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError("Camera is not available in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });
      setCameraStream(stream);
    } catch (err) {
      setCameraError(err instanceof Error ? err.message : "Camera permission was denied.");
    }
  }

  function captureCameraFrame() {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas || video.videoWidth === 0 || video.videoHeight === 0) {
      setCameraError("Camera frame is not ready yet.");
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setCameraError("Cannot capture from camera.");
      return;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setCameraError("Cannot capture from camera.");
          return;
        }

        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        selectFile(new File([blob], `camera-capture-${timestamp}.jpg`, { type: "image/jpeg" }), "camera");
        stopCamera();
      },
      "image/jpeg",
      0.94,
    );
  }

  async function processOneDocument(targetFile: File) {
    const formData = new FormData();
    formData.append("file", targetFile);
    formData.append("preprocess", String(preprocess));
    formData.append("preprocess_profile", preprocess ? preprocessProfile : "none");
    formData.append("smart_crop", String(smartCrop));

    const response = await fetch("/api/ocr/finance", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail ?? "OCR processing failed.");
    }

    return payload as OcrResponse;
  }

  async function processDocument() {
    if (!file && !batchItems.length) {
      setError("Choose a document before processing.");
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      if (batchItems.length > 0) {
        let latestResult: OcrResponse | null = null;
        let latestFile: File | null = null;

        for (const [index, item] of batchItems.entries()) {
          setActiveBatchId(item.id);
          setFile(item.file);
          setResult(null);
          setSelectedBlockIndex(0);
          setProgress(Math.round((index / batchItems.length) * 100));
          setBatchItems((current) =>
            current.map((candidate) =>
              candidate.id === item.id ? { ...candidate, status: "processing", error: undefined } : candidate,
            ),
          );

          try {
            const payload = await processOneDocument(item.file);
            latestResult = payload;
            latestFile = item.file;
            setResult(payload);
            setBatchItems((current) =>
              current.map((candidate) =>
                candidate.id === item.id
                  ? { ...candidate, status: "done", result: payload, error: undefined }
                  : candidate,
              ),
            );
          } catch (err) {
            const message = err instanceof Error ? err.message : "OCR processing failed.";
            setError(message);
            setBatchItems((current) =>
              current.map((candidate) =>
                candidate.id === item.id ? { ...candidate, status: "error", error: message } : candidate,
              ),
            );
          }
        }

        if (latestResult && latestFile) {
          setFile(latestFile);
          setResult(latestResult);
        }
      } else if (file) {
        const payload = await processOneDocument(file);
        setResult(payload);
      }

      setActiveTab(tabs[0]);
      setSelectedBlockIndex(0);
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
    setCameraError(null);
    setProgress(0);
    setBatchItems([]);
    setActiveBatchId(null);
    setSelectedBlockIndex(0);
    stopCamera();
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
                  selectFiles(event.dataTransfer.files);
                }}
                className={cn(
                  "flex min-h-48 w-full cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed bg-muted/35 px-4 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  isDragging && "border-secondary bg-secondary/10",
                )}
              >
                <UploadCloud className="mb-3 h-8 w-8 text-secondary" aria-hidden="true" />
                <span className="font-medium">Drop documents here</span>
                <span className="mt-1 text-sm text-muted-foreground">PNG, JPG, WEBP, TIFF, BMP, or PDF</span>
              </button>

              <Input
                ref={inputRef}
                type="file"
                multiple
                accept=".png,.jpg,.jpeg,.webp,.tif,.tiff,.bmp,.pdf"
                className="sr-only"
                onChange={(event) => selectFiles(event.target.files)}
              />

              <div className="rounded-md border bg-card p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium">Camera capture</div>
                    <div className="text-xs text-muted-foreground">Capture locally, then process when ready.</div>
                  </div>
                  {cameraStream ? (
                    <Button type="button" variant="ghost" size="sm" onClick={stopCamera}>
                      Close
                    </Button>
                  ) : (
                    <Button type="button" variant="outline" size="sm" onClick={startCamera}>
                      <Camera className="h-4 w-4" aria-hidden="true" />
                      Open
                    </Button>
                  )}
                </div>

                {cameraStream ? (
                  <div className="mt-3 space-y-3">
                    <div className="overflow-hidden rounded-md border bg-muted">
                      <video
                        ref={videoRef}
                        autoPlay
                        muted
                        playsInline
                        className="aspect-[4/3] w-full bg-black object-cover"
                      />
                    </div>
                    <Button type="button" className="w-full" onClick={captureCameraFrame}>
                      <Camera className="h-4 w-4" aria-hidden="true" />
                      Capture document
                    </Button>
                  </div>
                ) : null}

                {cameraError ? (
                  <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
                    {cameraError}
                  </div>
                ) : null}

                <canvas ref={canvasRef} className="hidden" />
              </div>

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

              {batchItems.length > 1 ? (
                <div className="rounded-md border bg-card p-3">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium">Batch queue</div>
                      <div className="text-xs text-muted-foreground">
                        {completedBatchCount}/{batchItems.length} documents completed
                      </div>
                    </div>
                    <Badge variant="outline">{batchItems.length} files</Badge>
                  </div>
                  <div className="max-h-48 space-y-2 overflow-auto">
                    {batchItems.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => openBatchItem(item)}
                        className={cn(
                          "grid w-full gap-2 rounded-md border px-3 py-2 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                          activeBatchId === item.id ? "border-secondary bg-secondary/10" : "bg-muted/30 hover:bg-muted",
                        )}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span className="truncate font-medium">{item.file.name}</span>
                          <Badge
                            variant={
                              item.status === "error"
                                ? "warning"
                                : item.status === "done"
                                  ? "secondary"
                                  : item.status === "processing"
                                    ? "warning"
                                    : "muted"
                            }
                          >
                            {item.status}
                          </Badge>
                        </div>
                        {item.error ? <div className="text-xs text-destructive">{item.error}</div> : null}
                      </button>
                    ))}
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

              <label className="grid gap-2 text-sm">
                <span className="font-medium">Preprocessing profile</span>
                <select
                  value={preprocessProfile}
                  disabled={!preprocess}
                  onChange={(event) => setPreprocessProfile(event.target.value)}
                  className="min-h-11 rounded-md border bg-card px-3 text-sm text-foreground shadow-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {preprocessProfiles.map((profile) => (
                    <option key={profile.value} value={profile.value}>
                      {profile.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex min-h-11 items-center gap-3 rounded-md border bg-card px-3 text-sm">
                <input
                  type="checkbox"
                  checked={smartCrop}
                  onChange={(event) => setSmartCrop(event.target.checked)}
                  className="h-4 w-4 rounded border-input accent-primary"
                />
                <span className="flex min-w-0 items-center gap-2">
                  <Crop className="h-4 w-4 text-secondary" aria-hidden="true" />
                  Smart crop document region
                </span>
              </label>

              {isProcessing ? (
                <div className="space-y-2">
                  <Progress value={progress} />
                  <div className="text-xs text-muted-foreground">
                    {batchItems.length > 1
                      ? `Processing batch ${completedBatchCount}/${batchItems.length}...`
                      : "Processing OCR and finance extraction..."}
                  </div>
                </div>
              ) : null}

              {error ? (
                <div className="flex gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>{error}</span>
                </div>
              ) : null}

              <Button type="button" className="w-full" disabled={(!file && !batchItems.length) || isProcessing} onClick={processDocument}>
                {isProcessing ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                {batchItems.length > 1 ? `Process ${batchItems.length} documents` : "Process OCR"}
              </Button>
            </CardContent>
          </Card>

          <div className="space-y-6">
            {result ? (
              <>
                <div className="grid gap-4 md:grid-cols-5">
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
                      <div className="pt-1 text-xs capitalize text-muted-foreground">
                        {result.preprocess_profile} profile
                      </div>
                    </CardHeader>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardDescription>Region</CardDescription>
                      <CardTitle>{result.smart_crop?.applied ? "Cropped" : "Full"}</CardTitle>
                      <div className="pt-1 text-xs text-muted-foreground">
                        {result.smart_crop?.applied
                          ? `${result.smart_crop.width}x${result.smart_crop.height}`
                          : "Original image"}
                      </div>
                    </CardHeader>
                  </Card>
                </div>

                {result.missing_fields.length || result.validation_errors.length ? (
                  <div className="rounded-lg border border-accent/40 bg-accent/10 p-4">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-accent-foreground" aria-hidden="true" />
                      <div className="min-w-0">
                        <div className="text-sm font-semibold">Needs review</div>
                        {result.missing_fields.length ? (
                          <div className="mt-2 flex flex-wrap gap-2">
                            {result.missing_fields.map((field) => (
                              <Badge key={field} variant="warning" className="capitalize">
                                Missing {field.replaceAll("_", " ")}
                              </Badge>
                            ))}
                          </div>
                        ) : null}
                        {result.validation_errors.length ? (
                          <ul className="mt-2 list-inside list-disc text-sm text-muted-foreground">
                            {result.validation_errors.map((validationError) => (
                              <li key={validationError}>{validationError}</li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ) : null}

                {result.layout_evidence.length ? (
                  <div className="rounded-lg border bg-card p-4">
                    <div className="text-sm font-semibold">Recovered by layout</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {result.layout_evidence.map((item) => (
                        <Badge key={`${item.field}-${item.value}`} variant="secondary" className="capitalize">
                          {item.field.replaceAll("_", " ")}: {String(item.value)}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null}

                <Card>
                  <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <CardTitle>Review Workspace</CardTitle>
                      <CardDescription>
                        {result.blocks.length} OCR blocks, {result.words.length} words,
                        {result.fields.length} extracted fields, {lowConfidenceCount} low-confidence blocks.
                      </CardDescription>
                    </div>
                    <Tabs tabs={tabs} value={activeTab} onValueChange={setActiveTab} />
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(420px,0.95fr)]">
                      <DocumentPreviewPanel
                        fileName={file?.name}
                        filePreviewUrl={filePreviewUrl}
                        imageSize={imageSize}
                        isImagePreview={isImagePreview}
                        isPdfPreview={isPdfPreview}
                        blocks={result.blocks}
                        selectedBlockIndex={selectedBlockIndex}
                        onImageLoad={(width, height) => setImageSize({ width, height })}
                        onSelectBlock={setSelectedBlockIndex}
                      />

                      <div className="min-w-0">
                        {activeTab === "Blocks" ? (
                          <BlockReviewPanel
                            blocks={result.blocks}
                            selectedBlock={selectedBlock}
                            selectedBlockIndex={selectedBlockIndex}
                            onSelectBlock={setSelectedBlockIndex}
                          />
                        ) : null}

                        {activeTab === "Words" ? (
                          <div className="grid max-h-[620px] gap-2 overflow-auto rounded-md border p-3 sm:grid-cols-2">
                            {result.words.map((word) => (
                              <div
                                key={word.id ?? `${word.page}-${word.block_id}-${word.index}-${word.text}`}
                                className="rounded-md border bg-card p-3"
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <div className="min-w-0">
                                    <div className="truncate text-sm font-medium">{word.text}</div>
                                    <div className="mt-1 text-xs text-muted-foreground">
                                      Page {word.page} - {word.block_id ?? "block"} - #{word.index + 1}
                                    </div>
                                  </div>
                                  <Badge variant={word.status === "needs_review" ? "warning" : "muted"}>
                                    {word.status === "needs_review" ? "Check" : "Ready"}
                                  </Badge>
                                </div>
                                <div className="mt-3">
                                  <ConfidenceBar value={word.confidence} />
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : null}

                        {activeTab === "Fields" ? (
                          <div className="max-h-[620px] overflow-auto rounded-md border">
                            {result.fields.length ? (
                              <table className="w-full text-left text-sm">
                                <thead className="sticky top-0 bg-muted text-xs uppercase text-muted-foreground">
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

                        {activeTab === "Full text" ? (
                          <pre className="max-h-[620px] overflow-auto rounded-md border bg-muted/40 p-4 text-sm leading-6 whitespace-pre-wrap">
                            {result.full_text || "No text detected"}
                          </pre>
                        ) : null}
                      </div>
                    </div>
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

type DocumentPreviewPanelProps = {
  fileName?: string;
  filePreviewUrl: string | null;
  imageSize: { width: number; height: number };
  isImagePreview: boolean;
  isPdfPreview: boolean;
  blocks: OcrBlock[];
  selectedBlockIndex: number;
  onImageLoad: (width: number, height: number) => void;
  onSelectBlock: (index: number) => void;
};

function DocumentPreviewPanel({
  fileName,
  filePreviewUrl,
  imageSize,
  isImagePreview,
  isPdfPreview,
  blocks,
  selectedBlockIndex,
  onImageLoad,
  onSelectBlock,
}: DocumentPreviewPanelProps) {
  return (
    <section className="min-w-0 rounded-md border bg-muted/30">
      <div className="flex min-h-14 items-center justify-between gap-3 border-b bg-card px-4 py-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold">Document preview</div>
          <div className="truncate text-xs text-muted-foreground">{fileName ?? "Processed document"}</div>
        </div>
        <Badge variant="outline">
          <ImageIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {isPdfPreview ? "PDF" : "Image"}
        </Badge>
      </div>

      <div className="flex h-[620px] items-start justify-center overflow-auto p-4">
        {isImagePreview && filePreviewUrl ? (
          <div className="relative inline-block max-w-full overflow-hidden rounded-md border bg-card shadow-sm">
            <img
              src={filePreviewUrl}
              alt="Uploaded finance document preview"
              className="block max-h-[560px] max-w-full object-contain"
              onLoad={(event) => {
                onImageLoad(event.currentTarget.naturalWidth, event.currentTarget.naturalHeight);
              }}
            />
            {imageSize.width > 0 && imageSize.height > 0 ? (
              <div className="pointer-events-none absolute inset-0">
                {blocks.map((block, index) => {
                  const isSelected = index === selectedBlockIndex;
                  return (
                    <button
                      key={`${block.page}-${index}-${block.text}`}
                      type="button"
                      aria-label={`Select OCR block ${index + 1}`}
                      onClick={() => onSelectBlock(index)}
                      className={cn(
                        "pointer-events-auto absolute rounded-sm border-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                        isSelected
                          ? "border-accent bg-accent/25 shadow-[0_0_0_2px_rgba(255,255,255,0.75)]"
                          : "border-secondary/80 bg-secondary/10 hover:bg-secondary/20",
                      )}
                      style={{
                        left: `${(block.bbox.x / imageSize.width) * 100}%`,
                        top: `${(block.bbox.y / imageSize.height) * 100}%`,
                        width: `${(block.bbox.width / imageSize.width) * 100}%`,
                        height: `${(block.bbox.height / imageSize.height) * 100}%`,
                      }}
                    />
                  );
                })}
              </div>
            ) : null}
          </div>
        ) : null}

        {isPdfPreview && filePreviewUrl ? (
          <iframe
            title="Uploaded PDF preview"
            src={filePreviewUrl}
            className="h-[560px] w-full rounded-md border bg-card"
          />
        ) : null}

        {!filePreviewUrl ? (
          <div className="flex min-h-72 w-full items-center justify-center rounded-md border border-dashed bg-card text-sm text-muted-foreground">
            Preview is available after selecting a document.
          </div>
        ) : null}
      </div>
    </section>
  );
}

type BlockReviewPanelProps = {
  blocks: OcrBlock[];
  selectedBlock: OcrBlock | null;
  selectedBlockIndex: number;
  onSelectBlock: (index: number) => void;
};

function BlockReviewPanel({
  blocks,
  selectedBlock,
  selectedBlockIndex,
  onSelectBlock,
}: BlockReviewPanelProps) {
  return (
    <section className="grid h-[620px] min-w-0 grid-rows-[auto_1fr] overflow-hidden rounded-md border bg-card">
      <div className="border-b bg-muted/45 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">OCR text blocks</div>
            <div className="text-xs text-muted-foreground">
              Select a text block to match it with the document area.
            </div>
          </div>
          <Badge variant={selectedBlock && selectedBlock.confidence < 0.75 ? "warning" : "muted"}>
            {selectedBlock ? `Block ${selectedBlockIndex + 1}` : "No block"}
          </Badge>
        </div>
      </div>

      <div className="overflow-auto">
        {blocks.length ? (
          blocks.map((block, index) => (
            <button
              key={`${block.page}-${index}-${block.text}`}
              type="button"
              onClick={() => onSelectBlock(index)}
              className={cn(
                "grid w-full gap-3 border-b p-4 text-left transition-colors last:border-b-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                selectedBlockIndex === index ? "bg-accent/10" : "hover:bg-muted/55",
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-medium leading-6">{block.text}</div>
                  {block.raw_text && block.raw_text !== block.text ? (
                    <div className="mt-1 text-xs leading-5 text-muted-foreground">Raw: {block.raw_text}</div>
                  ) : null}
                </div>
                <Badge variant={block.confidence >= 0.75 ? "muted" : "warning"}>
                  {block.confidence >= 0.75 ? "Ready" : "Check"}
                </Badge>
              </div>

              <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-[1fr_auto] sm:items-center">
                <div>
                  Page {block.page} - {block.type} - x{block.bbox.x} y{block.bbox.y}
                </div>
                <ConfidenceBar value={block.confidence} />
              </div>

              {block.words.length ? (
                <div className="flex flex-wrap gap-2">
                  {block.words.map((word) => (
                    <span
                      key={`${block.page}-${index}-${word.index}-${word.text}`}
                      className={cn(
                        "rounded-md border px-2 py-1 text-xs",
                        word.confidence < 0.75
                          ? "border-accent/50 bg-accent/15 text-foreground"
                          : "bg-muted text-muted-foreground",
                      )}
                    >
                      {word.text}
                    </span>
                  ))}
                </div>
              ) : null}
            </button>
          ))
        ) : (
          <div className="flex h-full items-center justify-center p-6 text-center text-sm text-muted-foreground">
            No OCR blocks were detected.
          </div>
        )}
      </div>
    </section>
  );
}
