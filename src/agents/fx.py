from typing import Dict, List

import pandas as pd

from src.tools.variance import filter_by_scope


class FXAgent:
    def analyze(self, df: pd.DataFrame, month: str, **filters) -> Dict:
        scoped = filter_by_scope(df, month, **filters)
        if scoped.empty:
            return {"summary": "No FX data for scope.", "signals": []}

        signals: List[Dict] = []
        summary_parts: List[str] = []

        try:
            prior_month = (pd.Period(month) - 1).strftime("%Y-%m")
        except Exception:
            prior_month = None

        if prior_month:
            prior_scoped = filter_by_scope(df, prior_month, **filters)
        else:
            prior_scoped = pd.DataFrame()

        for _, row in scoped.iterrows():
            pair = row.get("pair")
            rate = row.get("avg_rate")
            region = row.get("region")
            prior_rate = None
            if not prior_scoped.empty:
                match = prior_scoped[
                    (prior_scoped.get("pair") == pair) & (prior_scoped.get("region") == region)
                ]
                if not match.empty:
                    prior_rate = match.iloc[0]["avg_rate"]
            change = rate - prior_rate if prior_rate is not None else None
            if change is not None:
                signals.append(
                    {"type": "fx_change", "pair": pair, "region": region, "delta": change, "prior": prior_rate, "current": rate}
                )
                summary_parts.append(f"{region} {pair} change {change:+.3f}")
            else:
                summary_parts.append(f"{region} {pair} current {rate:.3f}")

        summary = "; ".join(summary_parts)
        return {"summary": summary, "signals": signals}
