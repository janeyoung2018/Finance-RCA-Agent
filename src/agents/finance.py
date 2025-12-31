from typing import Dict, List

import pandas as pd

from src.config import TOP_CONTRIBUTORS
from src.tools.variance import finance_variance, filter_by_scope, summarize_top_contributors


class FinanceVarianceAgent:
    def analyze(self, df: pd.DataFrame, month: str, comparison: str = "plan", **filters) -> Dict:
        scoped = filter_by_scope(df, month, **filters)
        if scoped.empty:
            return {"summary": "No finance data for scope.", "totals": {}, "top_contributors": []}

        var_df = finance_variance(scoped, comparison=comparison)
        if var_df.empty:
            return {"summary": "No variance available for scope.", "totals": {}, "top_contributors": []}

        totals = var_df.groupby("metric")["variance"].sum().to_dict()
        top = summarize_top_contributors(
            var_df, ["metric", "region", "bu", "product_line", "segment"], top_n=TOP_CONTRIBUTORS
        )

        summary_parts: List[str] = []
        for metric, value in totals.items():
            direction = "above" if value >= 0 else "below"
            summary_parts.append(f"{metric}: {abs(value):,.0f} {direction} {comparison}")
        summary = "; ".join(summary_parts) if summary_parts else "Variance computed."

        return {"summary": summary, "totals": totals, "top_contributors": top}
