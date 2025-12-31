export type Comparison = "plan" | "prior";

export interface RCARequest {
  month: string;
  region?: string;
  bu?: string;
  product_line?: string;
  segment?: string;
  comparison?: Comparison;
}

export interface RCAResponse {
  run_id: string;
  status: string;
  message: string;
  result?: Record<string, unknown> | null;
}
