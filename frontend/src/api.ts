import type { RCAListResponse, RCARequest, RCAResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function startRca(payload: RCARequest): Promise<RCAResponse> {
  const res = await fetch(`${API_BASE}/rca`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Failed to start RCA: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRca(runId: string): Promise<RCAResponse> {
  const res = await fetch(`${API_BASE}/rca/${runId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch RCA: ${res.statusText}`);
  }
  return res.json();
}

export async function listRcas(params?: { status?: string; limit?: number; offset?: number }): Promise<RCAListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));
  const res = await fetch(`${API_BASE}/rca?${query.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to list RCAs: ${res.statusText}`);
  }
  return res.json();
}
