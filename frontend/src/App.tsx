import { useEffect, useMemo, useState } from "react";
import { fetchRca, startRca } from "./api";
import { OPTION_VALUES } from "./optionValues";
import type { Domains, RCARequest, RCAResponse, Rollup } from "./types";

const DEFAULT_FORM: RCARequest = {
  month: "2025-08",
  comparison: "all",
  full_sweep: false,
};

const POLL_INTERVAL_MS = 1500;

function App() {
  const [form, setForm] = useState<RCARequest>(DEFAULT_FORM);
  const [submittedForm, setSubmittedForm] = useState<RCARequest | null>(null);
  const [currentRun, setCurrentRun] = useState<RCAResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

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

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (polling && currentRun?.run_id) {
      timer = setInterval(async () => {
        try {
          const res = await fetchRca(currentRun.run_id);
          setCurrentRun(res);
          if (res.status === "completed" || res.status === "failed") {
            setPolling(false);
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
  }, [polling, currentRun?.run_id]);

  const handleChange = (key: keyof RCARequest) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [key]: e.target.value || undefined }));
  };

  const handleToggle = (key: keyof RCARequest) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [key]: e.target.checked }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await startRca(form);
      setSubmittedForm({ ...form });
      setCurrentRun(res);
      setPolling(true);
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
          <p className="message">{currentRun.message}</p>
          {currentRun.result && (
            <>
              {renderDecisionSummaries(currentRun.result as any, filterChips, scopeLabel)}
              {renderRollup((currentRun.result as any).rollup as Rollup | undefined, filterChips, scopeLabel)}
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
    </div>
  );
}

export default App;

function renderRollup(rollup?: Rollup, filters: FilterChip[] = [], scopeLabel?: string) {
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
          {overall.metrics && <MetricTable metrics={overall.metrics} />}
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
              {data.metrics && <MetricTable metrics={data.metrics} />}
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
              {data.metrics && <MetricTable metrics={data.metrics} />}
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

function MetricTable({ metrics }: { metrics: Record<string, any> }) {
  const rows = Object.entries(metrics);
  if (rows.length === 0) return null;
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Metric</th>
          <th>Actual</th>
          <th>Plan</th>
          <th>Prior</th>
          <th>Var vs Plan</th>
          <th>Var vs Prior</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([metric, values]) => (
          <tr key={metric}>
            <td>{metric}</td>
            <td>{fmt(values.actual)}</td>
            <td>{fmt(values.plan)}</td>
            <td>{fmt(values.prior)}</td>
            <td>{fmt(values.variance_to_plan)}</td>
            <td>{fmt(values.variance_to_prior)}</td>
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
