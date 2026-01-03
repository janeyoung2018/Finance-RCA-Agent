export type Comparison = "plan" | "prior" | "all";

export interface RCARequest {
  month: string;
  region?: string;
  bu?: string;
  product_line?: string;
  segment?: string;
  metric?: string;
  comparison?: Comparison;
  full_sweep?: boolean;
}

export interface MetricSummary {
  actual: number;
  plan?: number | null;
  prior?: number | null;
  variance_to_plan?: number | null;
  variance_to_prior?: number | null;
}

export interface TopContribution {
  [key: string]: string | number;
  actual?: number;
  plan?: number;
  prior?: number;
  variance_to_plan?: number;
  variance_to_prior?: number;
}

export interface Rollup {
  overall?: {
    metrics?: Record<string, MetricSummary>;
    top_regions_by_metric?: Record<string, TopContribution[]>;
    top_bus_by_metric?: Record<string, TopContribution[]>;
  };
  regions?: Record<string, { metrics?: Record<string, MetricSummary>; top_bus_by_metric?: Record<string, TopContribution[]> }>;
  bus?: Record<string, { metrics?: Record<string, MetricSummary>; top_regions_by_metric?: Record<string, TopContribution[]> }>;
}

export interface DomainEntry {
  summary?: string;
  brief_report?: string;
  domains?: { domain: string; occurrences: number }[];
  llm_decision_summary?: string;
}

export interface Domains {
  regions?: Record<string, DomainEntry>;
  bus?: Record<string, DomainEntry>;
}

export interface RCAResponse {
  run_id: string;
  status: string;
  message: string;
  payload?: Record<string, unknown> | null;
  created_at?: number | null;
  updated_at?: number | null;
  result?: Record<string, unknown> | null;
}

export interface RCAListResponse {
  total: number;
  limit: number;
  offset: number;
  items: RCAResponse[];
}
