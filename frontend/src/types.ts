export interface Stage {
  n: number;
  name: string;
  lines: string[];
  data: Record<string, unknown>;
}

export interface ActionCard {
  action_id: string;
  action_type: string;
  object_id: string;
  target_title: string;
  tier: number;
  status: string;
  params: Record<string, number | string>;
  guards_passed: string[];
  reason: string | null;
  fallback: string | null;
  rollback: string | null;
  connector_write: string;
}

export interface Candidate {
  target_type: string;
  target_id: string;
  label: string;
  confidence: number;
}

export interface AskResult {
  question: string;
  domain: string;
  stages: Stage[];
  answer?: string;
  citations?: string[];
  action_card?: ActionCard | null;
  confidence?: number;
  status: string;
  context_block?: string;
  agent?: { source: string; model: string; ctx_tokens: number };
  clarification?: { surface: string; confidence: number; candidates: Candidate[] };
  error?: string;
}

export interface DomainInfo {
  name: string;
  label: string;
  flagship: string;
  samples: string[];
  primary_type: string;
}

export interface WindowDef {
  window: string;
  starts_in_days: number;
  duration_days: number;
  expected_uplift_pct: number;
}

export type ObjectRow = {
  object_id: string;
  key: string;
  title: string;
  top: boolean;
} & Record<string, string | number | boolean | null>;

export interface ObjectsView {
  domain: string;
  label: string;
  columns: string[];
  rows: ObjectRow[];
  window: WindowDef | null;
  object_set: string;
  unit: string;
  flagship: string;
  samples: string[];
}

export interface SignalResult {
  domain: string;
  signal: { type: string; key: string };
  lifted: {
    event_type: string;
    variant: string;
    title: string;
    position: string | null;
    severity: string;
  };
  severity_trace: string[];
  proposal: ActionCard;
  fallback: ActionCard | null;
}

export interface Health {
  status: string;
  ontology_version: string;
  llm_available: boolean;
  provider: string | null;
}
