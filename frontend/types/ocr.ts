export type OcrField = {
  name: string;
  value: string;
  confidence: number;
};

export type OcrBlock = {
  text: string;
  raw_text?: string | null;
  type: string;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  confidence: number;
  page: number;
  words: OcrWord[];
};

export type OcrWord = {
  id?: string;
  level?: "word";
  text: string;
  raw_text?: string | null;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  confidence: number;
  page: number;
  index: number;
  status?: "ready" | "needs_review";
  block_id?: string;
  block_text?: string;
  source?: string;
};

export type OcrReviewItem = {
  id: string;
  level: "block";
  text: string;
  raw_text?: string | null;
  type: string;
  bbox: OcrBlock["bbox"];
  confidence: number;
  page: number;
  status: "ready" | "needs_review";
  words: OcrWord[];
};

export type LayoutEvidence = {
  field: string;
  value: string | number;
  source: string;
};

export type OcrResponse = {
  success: boolean;
  doc_type: string;
  classification_confidence: number;
  page_count: number;
  preprocess_profile: string;
  required_fields: string[];
  missing_fields: string[];
  layout_evidence: LayoutEvidence[];
  validation_errors: string[];
  full_text: string;
  markdown: string;
  fields: OcrField[];
  blocks: OcrBlock[];
  review_items: OcrReviewItem[];
  words: OcrWord[];
  processing_time: number;
  filename: string;
};

export type HealthResponse = {
  status: string;
  engine: string;
  ocr_device: string;
  ocr_detection_model: string;
  ocr_recognition_model: string;
  ocr_return_word_box: boolean;
  pdf_dpi: number;
  preprocess_enabled: boolean;
  preprocess_profile: string;
  finance_extraction_enabled: boolean;
};
