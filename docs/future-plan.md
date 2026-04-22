# Future Plan

This roadmap turns the OCR backend into a finance document operations workflow.

## Implemented From This Plan

- Batch upload in the Next.js review UI.
- Optional smart crop/document region detection for image uploads.
- Smart crop metadata in the API response while keeping OCR boxes aligned to the original preview.

## Near Term

1. Editable extracted fields UI
   - users can correct OCR/extractor output before approval
   - keep raw OCR value and corrected value separately
2. Document statuses
   - `uploaded`
   - `processing`
   - `needs_review`
   - `approved`
   - `rejected`
   - `exported`
3. Required field rules per document type
   - receipt: total, date, merchant, currency
   - payment slip: amount, transfer date, reference number, currency
   - invoice: invoice number, date, vendor, total, tax
   - tax invoice: NPWP, faktur number, DPP, PPN, total
4. Validation engine
   - totals and tax consistency
   - amount paid greater than or equal to total
   - valid NPWP/account/reference shape
   - dates not in impossible ranges
5. Batch upload
   - current: upload many documents and process sequentially in the frontend
   - next: move batch work to a backend job queue with persistence
   - next: review only failed/low-confidence documents
6. Smart crop/document region
   - current: detect likely document region for image uploads
   - current: run OCR on cropped image
   - current: keep returned boxes aligned with original preview
   - next: add optional perspective correction after enough evaluation samples exist

## Workflow

7. Human review and approval
   - reviewer edits extracted fields
   - approver approves/rejects document
   - approval locks final data for export
8. Audit trail
   - field changed
   - OCR value vs corrected value
   - reviewer identity
   - approval/export timestamp
9. Export
   - CSV
   - JSON
   - Excel
   - accounting import templates
10. Duplicate detection
   - file hash
   - transaction ID
   - invoice number
   - merchant/date/total similarity

## Security And Privacy

11. Sensitive data masking
   - account numbers
   - phone numbers
   - NPWP
   - tax IDs
12. Role-based UX
   - viewer sees masked data
   - reviewer can correct
   - admin can export and manage settings
13. Document retention
   - process in memory by default
   - encrypted storage when persistence is required
   - retention policy per workspace

## Advanced Finance Features

14. Reconciliation
   - match invoice with payment proof
   - match receipt with reimbursement claim
   - match payment slip with bank statement
15. Vendor/bank templates
   - DANA payment proof
   - BCA/Mandiri/BRI transfer proof
   - marketplace invoices
   - recurring vendor layouts
16. Evaluation dashboard
   - missing field rate
   - correction rate
   - processing latency
   - confidence distribution
   - preprocessing profile performance
17. OCR job queue
   - async job status
   - retry failed OCR jobs
   - scale workers separately from API

## Recommended Priority

1. Editable fields and approval flow
2. Required field validation
3. Export CSV/JSON
4. Duplicate detection
5. Batch queue backed by persistence
6. Audit trail
7. Masking and role-based access
8. Reconciliation
