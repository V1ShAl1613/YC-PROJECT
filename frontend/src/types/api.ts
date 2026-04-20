// ─── types/api.ts ────────────────────────────────────────────────────────────
export interface Citation {
  id: string;
  case_name: string;
  court: string;
  year: number;
  paragraph: string;
  url?: string;
  source: string;
  relevance_score: number;
}

export interface ValidationResult {
  citation_verified: boolean;
  cross_consistent: boolean;
  confidence_score: number;
  confidence_label: "HIGH" | "MEDIUM" | "LOW" | "NONE";
  rejection_reasons: string[];
}

export interface QueryResponse {
  query: string;
  answer: string;
  citations: Citation[];
  validation: ValidationResult;
  fallback: boolean;
  latency_ms: number;
  agent_trace?: string[];
}
