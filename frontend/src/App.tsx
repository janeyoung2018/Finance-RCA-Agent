import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { fetchRca, listRcas, startRca } from "./api";
import { OPTION_VALUES } from "./optionValues";
import type { Comparison, Domains, RCARequest, RCAResponse, Rollup } from "./types";

const DEFAULT_FORM: RCARequest = {
  month: "2025-08",
  comparison: "all",
  full_sweep: false,
};

const POLL_INTERVAL_MS = 1500;
const HISTORY_PAGE_SIZE = 10;
const RUN_QUERY_KEY = "run";

function App() {
  const [form, setForm] = useState<RCARequest>(DEFAULT_FORM);
  const [submittedForm, setSubmittedForm] = useState<RCARequest | null>(null);
  const [currentRun, setCurrentRun] = useState<RCAResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const [history, setHistory] = useState<RCAResponse[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyStatus, setHistoryStatus] = useState<string>("");
  const [historyPage, setHistoryPage] = useState(0);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [comparisonView, setComparisonView] = useState<Comparison | "all">("all");
  const [copiedRunId, setCopiedRunId] = useState<string | null>(null);

  const canSubmit = useMemo(() => Boolean(form.month), [form.month]);
  const resultPayload = currentRun?.result as any;
  const resultFilters = useMemo(() => {
    if (!resultPayload) return undefined;
    const merged = { ...(resultPayload.filters || {}) };
    if (resultPayload.month) merged.month = resultPayload.month;
    if (resultPayload.comparison) merged.comparison = resultPayload.comparison;
    return merged;
  }, [resultPayload]);
  const filterSource = resultFilters ?? submittedForm ?? undefined;
  const filterChips = useMemo(() => buildFilterChips(filterSource), [filterSource]);
  const scopeLabel =
    (resultPayload?.scope as string | undefined) || (resultPayload?.scopes ? "portfolio sweep" : undefined);
  const comparisonNote = useMemo(() => renderComparisonNote(filterSource), [filterSource]);

  const refreshHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const res = await listRcas({
        status: historyStatus || undefined,
        limit: HISTORY_PAGE_SIZE,
        offset: historyPage * HISTORY_PAGE_SIZE,
      });
      setHistory(res.items);
      setHistoryTotal(res.total);
    } catch (err) {
      console.error(err);
      setError((err as Error).message);
    } finally {
      setLoadingHistory(false);
    }
  }, [historyStatus, historyPage]);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (polling && currentRun?.run_id) {
      timer = setInterval(async () => {
        try {
          const res = await fetchRca(currentRun.run_id);
          setCurrentRun(res);
          if (res.status === "completed" || res.status === "failed") {
            setPolling(false);
            refreshHistory();
          }
        } catch (err) {
          console.error(err);
          setError((err as Error).message);
          setPolling(false);
        }
      }, POLL_INTERVAL_MS);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [polling, currentRun?.run_id, refreshHistory]);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  useEffect(() => {
    const url = new URL(window.location.href);
    const runId = url.searchParams.get(RUN_QUERY_KEY);
    if (runId) {
      handleLoadRun(runId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const comparison = (filterSource as any)?.comparison as Comparison | undefined;
    setComparisonView(comparison ?? "all");
  }, [filterSource]);

  const handleChange = (key: keyof RCARequest) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [key]: e.target.value || undefined }));
  };

  const handleToggle = (key: keyof RCARequest) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [key]: e.target.checked }));
  };

  const updateRunQueryParam = (runId?: string) => {
    const url = new URL(window.location.href);
    if (runId) {
      url.searchParams.set(RUN_QUERY_KEY, runId);
    } else {
      url.searchParams.delete(RUN_QUERY_KEY);
    }
    window.history.replaceState({}, "", url.toString());
  };

  const handleCopyLink = async (runId: string) => {
    const url = new URL(window.location.href);
    url.searchParams.set(RUN_QUERY_KEY, runId);
    try {
      await navigator.clipboard.writeText(url.toString());
      setCopiedRunId(runId);
      setTimeout(() => setCopiedRunId(null), 1600);
    } catch (err) {
      console.error(err);
      setError("Copy failed; you can manually copy the URL.");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await startRca(form);
      setSubmittedForm({ ...form });
      setCurrentRun(res);
      updateRunQueryParam(res.run_id);
      setPolling(true);
      setHistoryPage(0);
      refreshHistory();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleLoadRun = async (runId: string) => {
    setError(null);
    try {
      const res = await fetchRca(runId);
      setCurrentRun(res);
      updateRunQueryParam(runId);
      const payload = res.payload as RCARequest | undefined;
      if (payload?.month) setSubmittedForm(payload);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="page">
      <header>
        <h1>Finance RCA</h1>
        <p>Trigger a root cause analysis and watch results update.</p>
      </header>

      <form className="card" onSubmit={handleSubmit}>
        <div className="grid">
          <label>
            <span>Month (YYYY-MM)</span>
            <input value={form.month ?? ""} onChange={handleChange("month")} required placeholder="2025-08" />
          </label>
          <label>
            <span>Region</span>
            <select value={form.region ?? ""} onChange={handleChange("region")}>
              <option value="">All (sweep)</option>
              {OPTION_VALUES.regions.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>BU</span>
            <select value={form.bu ?? ""} onChange={handleChange("bu")}>
              <option value="">All (sweep)</option>
              {OPTION_VALUES.bus.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Product Line</span>
            <select value={form.product_line ?? ""} onChange={handleChange("product_line")}>
              <option value="">All (sweep)</option>
              {OPTION_VALUES.product_lines.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Segment</span>
            <select value={form.segment ?? ""} onChange={handleChange("segment")}>
              <option value="">All (sweep)</option>
              {OPTION_VALUES.segments.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Metric</span>
            <select value={form.metric ?? ""} onChange={handleChange("metric")}>
              <option value="">All (sweep)</option>
              {OPTION_VALUES.metrics.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Comparison</span>
            <select value={form.comparison ?? "plan"} onChange={handleChange("comparison")}>
              {OPTION_VALUES.comparisons.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>
        <button type="submit" disabled={!canSubmit}>
          {polling ? "Running..." : "Start RCA"}
        </button>
        <label className="checkbox">
          <input type="checkbox" checked={form.full_sweep ?? false} onChange={handleToggle("full_sweep")} />
          <span>Run full-sweep RCA across regions, BUs, product lines, and segments</span>
        </label>
        <p className="hint">Leave scope fields blank to sweep all slices for the selected month.</p>
        {error && <p className="error">{error}</p>}
      </form>

      {currentRun && (
        <div className="card">
          <div className="status-row">
            <div>
              <div className="label">Run ID</div>
              <div className="value">{currentRun.run_id}</div>
            </div>
            <div>
              <div className="label">Status</div>
              <div className={`status status-${currentRun.status}`}>{currentRun.status}</div>
            </div>
          </div>
          <div className="action-row">
            <div className="compare-toggle">
              <div className="label">Comparison view</div>
              <div className="pill-toggle">
                {(["all", "plan", "prior"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    className={comparisonView === mode ? "pill active" : "pill"}
                    onClick={() => setComparisonView(mode)}
                  >
                    {mode === "all" ? "Plan & Prior" : mode === "plan" ? "Plan only" : "Prior only"}
                  </button>
                ))}
              </div>
            </div>
            <div className="link-actions">
              <button type="button" className="ghost-button" onClick={() => handleCopyLink(currentRun.run_id)}>
                Copy deep-link
              </button>
              {copiedRunId === currentRun.run_id && <span className="hint muted">Link copied</span>}
            </div>
          </div>
          <p className="message">{currentRun.message}</p>
          {comparisonNote}
          {currentRun.result && (
            <>
              {renderDecisionSummaries(currentRun.result as any, filterChips, scopeLabel)}
              {renderRollup((currentRun.result as any).rollup as Rollup | undefined, filterChips, scopeLabel, comparisonView)}
              {renderDomains((currentRun.result as any).domains as Domains | undefined)}
            </>
          )}
          {currentRun.result && (
            <details open>
              <summary>Results</summary>
              <pre>{JSON.stringify(currentRun.result, null, 2)}</pre>
            </details>
          )}
        </div>
      )}

      <div className="card">
        <div className="section-header">
          <div>
            <h3>Recent Runs</h3>
            <p className="message">Persisted history powered by the durable run store.</p>
          </div>
          <div className="history-controls">
            <select value={historyStatus} onChange={(e) => setHistoryStatus(e.target.value)}>
              <option value="">All statuses</option>
              <option value="queued">Queued</option>
              <option value="running">Running</option>
              <option value="synthesizing">Synthesizing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
            <button type="button" onClick={() => refreshHistory()} disabled={loadingHistory}>
              {loadingHistory ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>
        <div className="history-meta">
          <span>
            Showing{" "}
            {historyTotal === 0
              ? "0"
              : `${historyPage * HISTORY_PAGE_SIZE + 1}-${Math.min((historyPage + 1) * HISTORY_PAGE_SIZE, historyTotal)}`}{" "}
            of {historyTotal}
          </span>
          <div className="pager">
            <button
              type="button"
              disabled={historyPage === 0 || loadingHistory}
              onClick={() => setHistoryPage((p) => Math.max(0, p - 1))}
            >
              Prev
            </button>
            <button
              type="button"
              disabled={(historyPage + 1) * HISTORY_PAGE_SIZE >= historyTotal || loadingHistory}
              onClick={() => setHistoryPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Status</th>
                <th>Scope</th>
                <th>Comparison</th>
                <th>Updated</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 && (
                <tr>
                  <td colSpan={6}>{loadingHistory ? "Loading..." : "No runs yet."}</td>
                </tr>
              )}
              {history.map((run) => (
                <tr key={run.run_id}>
                  <td className="mono">{run.run_id}</td>
                  <td>
                    <span className={`status status-${run.status}`}>{run.status}</span>
                  </td>
                  <td>{formatScope(run.payload)}</td>
                  <td>{formatComparison(run.payload)}</td>
                  <td>{fmtTime(run.updated_at)}</td>
                  <td>
                    <button type="button" onClick={() => handleLoadRun(run.run_id)}>
                      Load
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default App;

function renderRollup(rollup?: Rollup, filters: FilterChip[] = [], scopeLabel?: string, comparisonView: Comparison | "all" = "all") {
  if (!rollup) return null;
  const overall = rollup.overall;
  const regions = rollup.regions;
  const bus = rollup.bus;
  return (
    <div className="rollup">
      <div className="section-header">
        <h3>Finance Rollup (Actual vs Plan/Prior)</h3>
        <FilterBar chips={filters} scopeLabel={scopeLabel} />
      </div>
      {overall && (
        <div className="rollup-section">
          <h4>Overall</h4>
          {overall.metrics && <MetricTable metrics={overall.metrics} comparisonView={comparisonView} />}
          {overall.top_regions_by_metric &&
            Object.entries(overall.top_regions_by_metric).map(([metric, rows]) =>
              rows.length ? <TopTable key={`reg-${metric}`} title={`Top Regions (${metric})`} rows={rows} /> : null
            )}
          {overall.top_bus_by_metric &&
            Object.entries(overall.top_bus_by_metric).map(([metric, rows]) =>
              rows.length ? <TopTable key={`bu-${metric}`} title={`Top BUs (${metric})`} rows={rows} /> : null
            )}
        </div>
      )}
      {regions && Object.keys(regions).length > 0 && (
        <div className="rollup-section">
          <h4>By Region</h4>
          {Object.entries(regions).map(([name, data]) => (
            <div key={name} className="rollup-subsection">
              <strong>{name}</strong>
              {data.metrics && <MetricTable metrics={data.metrics} comparisonView={comparisonView} />}
              {data.top_bus_by_metric &&
                Object.entries(data.top_bus_by_metric).map(([metric, rows]) =>
                  rows.length ? <TopTable key={`${name}-bu-${metric}`} title={`Top BUs (${metric})`} rows={rows} /> : null
                )}
            </div>
          ))}
        </div>
      )}
      {bus && Object.keys(bus).length > 0 && (
        <div className="rollup-section">
          <h4>By BU</h4>
          {Object.entries(bus).map(([name, data]) => (
            <div key={name} className="rollup-subsection">
              <strong>{name}</strong>
              {data.metrics && <MetricTable metrics={data.metrics} comparisonView={comparisonView} />}
              {data.top_regions_by_metric &&
                Object.entries(data.top_regions_by_metric).map(([metric, rows]) =>
                  rows.length ? (
                    <TopTable key={`${name}-reg-${metric}`} title={`Top Regions (${metric})`} rows={rows} />
                  ) : null
                )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function renderDomains(domains?: Domains) {
  if (!domains) return null;
  const { regions, bus } = domains;
  const hasRegions = regions && Object.keys(regions).length > 0;
  const hasBus = bus && Object.keys(bus).length > 0;
  if (!hasRegions && !hasBus) return null;
  return (
    <div className="domains">
      <h3>Domain Drivers</h3>
      {hasRegions && (
        <div className="domain-section">
          <h4>By Region</h4>
          {Object.entries(regions as NonNullable<typeof regions>).map(([name, entry]) => (
            <DomainCard key={name} name={name} entry={entry} />
          ))}
        </div>
      )}
      {hasBus && (
        <div className="domain-section">
          <h4>By BU</h4>
          {Object.entries(bus as NonNullable<typeof bus>).map(([name, entry]) => (
            <DomainCard key={name} name={name} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}

function renderDecisionSummaries(result: any, filters: FilterChip[] = [], scopeLabel?: string) {
  const scopeSynthesis = result?.synthesis as any;
  const portfolio = result?.portfolio as any;

  const scopeRule = scopeSynthesis?.rule_summary ?? scopeSynthesis?.summary;
  const scopeDecision = scopeSynthesis?.llm_decision_summary;
  const portfolioRule = portfolio?.rule_portfolio_brief ?? portfolio?.portfolio_brief;
  const portfolioDecision = portfolio?.llm_decision_summary;

  // Only show decision-support section when an LLM decision summary exists.
  if (!scopeDecision && !portfolioDecision) return null;

  return (
    <div className="domains">
      <div className="section-header">
        <h3>Decision Support Summaries</h3>
        <FilterBar chips={filters} scopeLabel={scopeLabel} />
      </div>
      {scopeDecision && (
        <div className="domain-card">
          <div className="domain-header">
            <span className="chip chip-ghost">Scope decision</span>
            {scopeLabel && <span className="chip chip-muted">{scopeLabel}</span>}
          </div>
          {renderDecisionText(scopeDecision)}
          {scopeRule && <p className="brief muted">{scopeRule}</p>}
        </div>
      )}
      {portfolioDecision && (
        <div className="domain-card">
          <div className="domain-header">
            <span className="chip chip-ghost">Portfolio sweep</span>
          </div>
          {renderDecisionText(portfolioDecision)}
          {portfolioRule && <p className="brief muted">{portfolioRule}</p>}
        </div>
      )}
    </div>
  );
}

function MetricTable({ metrics, comparisonView }: { metrics: Record<string, any>; comparisonView: Comparison | "all" }) {
  const rows = Object.entries(metrics);
  if (rows.length === 0) return null;
  const showPlan = comparisonView === "plan" || comparisonView === "all";
  const showPrior = comparisonView === "prior" || comparisonView === "all";
  type Column = { key: string; label: string; render: (metric: string, values: any) => ReactNode };
  const columns: Column[] = [
    { key: "metric", label: "Metric", render: (metric) => metric },
    { key: "actual", label: "Actual", render: (_, values) => fmt(values.actual) },
    showPlan ? { key: "plan", label: "Plan", render: (_, values) => fmt(values.plan) } : null,
    showPrior ? { key: "prior", label: "Prior", render: (_, values) => fmt(values.prior) } : null,
    showPlan ? { key: "variance_to_plan", label: "Var vs Plan", render: (_, values) => fmt(values.variance_to_plan) } : null,
    showPrior ? { key: "variance_to_prior", label: "Var vs Prior", render: (_, values) => fmt(values.variance_to_prior) } : null,
  ].filter(Boolean) as Column[];
  return (
    <table className="table">
      <thead>
        <tr>
          {columns.map((col) => (
            <th key={col.key}>{col.label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map(([metric, values]) => (
          <tr key={metric}>
            {columns.map((col) => (
              <td key={col.key}>{col.render(metric, values)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TopTable({ title, rows }: { title: string; rows: Record<string, any>[] }) {
  if (!rows || rows.length === 0) return null;
  const headers = Object.keys(rows[0]);
  return (
    <div className="top-table">
      <h5>{title}</h5>
      <table className="table">
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={idx}>
              {headers.map((h) => (
                <td key={h}>{fmt(row[h])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DomainCard({ name, entry }: { name: string; entry: any }) {
  const domains = entry.domains as { domain: string; occurrences: number }[] | undefined;
  return (
    <div className="domain-card">
      <div className="domain-header">
        <strong>{name}</strong>
        {entry.summary && <span className="chip">{entry.summary}</span>}
      </div>
      {entry.brief_report && <p className="brief">{entry.brief_report}</p>}
      {domains && domains.length > 0 && (
        <ul className="chips">
          {domains.map((d) => (
            <li key={d.domain} className="chip">
              {d.domain} ({d.occurrences})
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

type FilterChip = { label: string; value: string };

function buildFilterChips(filters?: Record<string, any> | null): FilterChip[] {
  if (!filters) return [];
  const mapping: [keyof RCARequest | "month" | "comparison", string][] = [
    ["month", "Month"],
    ["comparison", "Comparison"],
    ["region", "Region"],
    ["bu", "BU"],
    ["product_line", "Product Line"],
    ["segment", "Segment"],
    ["metric", "Metric"],
  ];
  const chips: FilterChip[] = [];
  for (const [key, label] of mapping) {
    const value = (filters as any)[key];
    if (value !== undefined && value !== null && value !== "") {
      chips.push({ label, value: String(value) });
    }
  }
  return chips;
}

function renderComparisonNote(filters?: Record<string, any> | null) {
  const comparison = (filters as any)?.comparison;
  if (!comparison || comparison === "plan" || comparison === "prior") return null;
  return <p className="hint muted">Comparison mode “all” shows plan and prior variances side-by-side.</p>;
}

function FilterBar({ chips, scopeLabel }: { chips: FilterChip[]; scopeLabel?: string }) {
  if ((!chips || chips.length === 0) && !scopeLabel) return null;
  return (
    <div className="filter-bar">
      {scopeLabel && <span className="chip chip-muted">Scope: {scopeLabel}</span>}
      {chips.map((chip) => (
        <span key={`${chip.label}-${chip.value}`} className="chip chip-ghost">
          {chip.label}: {chip.value}
        </span>
      ))}
    </div>
  );
}

function renderDecisionText(text: string) {
  const cleaned = (text || "").replace(/\*\*/g, "");
  if (!cleaned.trim()) return null;
  return cleaned.split(/\n+/).map((line, idx) => (
    <p key={idx} className="brief">
      {line.trim()}
    </p>
  ));
}

function fmt(value: any) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    if (Math.abs(value) >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}

function formatScope(payload?: Record<string, any> | null) {
  if (!payload) return "—";
  const parts = ["month", "region", "bu", "product_line", "segment", "metric"]
    .map((key) => (payload as any)[key])
    .filter(Boolean);
  return parts.length > 0 ? parts.join(" / ") : "full sweep";
}

function formatComparison(payload?: Record<string, any> | null) {
  if (!payload || !("comparison" in payload)) return "plan/prior";
  const value = (payload as any).comparison;
  if (value === "all") return "plan & prior";
  return String(value);
}

function fmtTime(ts?: number | null) {
  if (!ts) return "—";
  const date = new Date(ts * 1000);
  return date.toLocaleString();
}
