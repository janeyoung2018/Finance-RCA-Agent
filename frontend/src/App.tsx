import { useEffect, useMemo, useState } from "react";
import { fetchRca, startRca } from "./api";
import type { RCARequest, RCAResponse } from "./types";

const DEFAULT_FORM: RCARequest = {
  month: "2025-08",
  region: "APAC",
  bu: "Growth",
  comparison: "plan",
};

const POLL_INTERVAL_MS = 1500;

function App() {
  const [form, setForm] = useState<RCARequest>(DEFAULT_FORM);
  const [currentRun, setCurrentRun] = useState<RCAResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

  const canSubmit = useMemo(() => Boolean(form.month), [form.month]);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await startRca(form);
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
            <input value={form.region ?? ""} onChange={handleChange("region")} placeholder="APAC" />
          </label>
          <label>
            <span>BU</span>
            <input value={form.bu ?? ""} onChange={handleChange("bu")} placeholder="Growth" />
          </label>
          <label>
            <span>Product Line</span>
            <input value={form.product_line ?? ""} onChange={handleChange("product_line")} placeholder="Gamma" />
          </label>
          <label>
            <span>Segment</span>
            <input value={form.segment ?? ""} onChange={handleChange("segment")} placeholder="Enterprise" />
          </label>
          <label>
            <span>Comparison</span>
            <select value={form.comparison ?? "plan"} onChange={handleChange("comparison")}>
              <option value="plan">Plan</option>
              <option value="prior">Prior</option>
            </select>
          </label>
        </div>
        <button type="submit" disabled={!canSubmit}>
          {polling ? "Running..." : "Start RCA"}
        </button>
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
