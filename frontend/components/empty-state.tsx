import { FileSearch } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex min-h-80 flex-col items-center justify-center rounded-lg border border-dashed bg-card p-8 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-md bg-muted">
        <FileSearch className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
      </div>
      <h2 className="text-lg font-semibold">No document processed</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
        Upload an invoice, receipt, payment proof, tax document, or PDF to review OCR text,
        confidence, and extracted finance fields.
      </p>
    </div>
  );
}
