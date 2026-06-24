export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  meta?: {
    page?: number;
    page_size?: number;
    total?: number;
  };
}

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  name: string | null;
  role: string;
  created_at: string;
}

export interface AuthPayload {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Contract {
  id: string;
  title: string | null;
  file_url: string;
  file_type: string;
  file_size: number | null;
  contract_type: string | null;
  status: string;
  created_at: string;
  updated_at: string | null;
  latest_review?: ReviewBrief | null;
}

export interface ContractDetail extends Contract {
  tenant_id: string;
  user_id: string;
  page_count: number | null;
}

// --- Review types ---

export interface ReviewBrief {
  id: string;
  status: string;
  progress: number;
  summary: ReviewSummary | null;
  reviewed_draft?: boolean;
  error_detail?: string | null;
  created_at: string;
}

export interface Review {
  id: string;
  contract_id: string;
  status: string;
  progress: number;
  current_stage: string | null;
  schema_version: string;
  reviewed_draft?: boolean;
  error_detail?: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ReviewSummary {
  total_risks: number;
  high: number;
  medium: number;
  low: number;
}

export interface ReviewRiskItem {
  clause_id: string;
  clause_code: string;
  risk_level: string;
  risk_category: string;
  original_text: string;
  legal_analysis: string;
  legal_basis: string;
  basis_excerpt: string;
  basis_source: string;
  plain_explanation: string;
  suggested_revision: string;
  confidence: number;
}

export interface ReviewMissingClause {
  name: string;
  reason: string;
}

export interface ReviewContradiction {
  clause_a: string;
  clause_b: string;
  conflict_type: string;
  description: string;
}

export interface ReviewLLMMeta {
  provider_model: string;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
  finish_reason: string | null;
}

export interface ReviewRAGMeta {
  enabled: boolean;
  hit_count: number;
  mode: string;
  queries: string[];
}

export interface ReviewReport {
  id: string;
  contract_id: string;
  contract_title: string | null;
  status: string;
  progress: number;
  current_stage: string | null;
  schema_version: string;
  reviewed_draft?: boolean;
  summary: ReviewSummary | null;
  risks: ReviewRiskItem[];
  contradictions: ReviewContradiction[];
  missing_clauses: ReviewMissingClause[];
  llm_meta: ReviewLLMMeta | null;
  rag_meta: ReviewRAGMeta | null;
  disclaimer: string | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

// --- Phase 4: WebSocket types ---

export interface WSTicket {
  ticket: string;
  expires_in: number;
  review_id: string;
}

export interface WSStageEvent {
  event: "stage";
  review_id: string;
  task_id: string;
  stage: string;
  progress: number;
  detail: string;
  clause_current?: number;
  clause_total?: number;
  eta_sec?: number;
}

export interface WSCompleteEvent {
  event: "complete";
  review_id: string;
  task_id: string;
  summary: ReviewSummary;
  duration_sec: number;
}

export interface WSFailedEvent {
  event: "failed";
  review_id: string;
  task_id: string;
  code: number;
  message: string;
  detail: string;
  retryable: boolean;
}

export interface WSPingEvent {
  event: "ping";
}

export type WSEvent = WSStageEvent | WSCompleteEvent | WSFailedEvent | WSPingEvent;
