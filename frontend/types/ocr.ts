export type OcrField = {
  name: string;
  value: string;
  confidence: number;
};

export type OcrBlock = {
  text: string;
  type: string;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  confidence: number;
  page: number;
};

export type OcrResponse = {
  success: boolean;
  doc_type: string;
  classification_confidence: number;
  page_count: number;
  full_text: string;
  markdown: string;
  fields: OcrField[];
  blocks: OcrBlock[];
  processing_time: number;
  filename: string;
};

export type HealthResponse = {
  status: string;
  engine: string;
  ocr_device: string;
  ocr_detection_model: string;
  ocr_recognition_model: string;
  pdf_dpi: number;
  preprocess_enabled: boolean;
  finance_extraction_enabled: boolean;
};
