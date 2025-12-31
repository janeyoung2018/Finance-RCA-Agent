from typing import Dict, List

import pandas as pd

from src.tools.variance import filter_by_scope


class SupplyAgent:
    def analyze(self, df: pd.DataFrame, month: str, **filters) -> Dict:
        scoped = filter_by_scope(df, month, **filters)
        if scoped.empty:
            return {"summary": "No supply data for scope.", "signals": []}

        signals: List[Dict] = []
        avg_otif = scoped["otif"].mean()
        avg_lead = scoped["lead_time_days"].mean()
        summary = f"Avg OTIF {avg_otif:.2f}, lead time {avg_lead:.1f} days."

        worst_otif = scoped.sort_values("otif").head(3)
        for _, row in worst_otif.iterrows():
            signals.append(
                {
                    "type": "low_otif",
                    "otif": row["otif"],
                    "region": row.get("region"),
                    "bu": row.get("bu"),
                    "product_line": row.get("product_line"),
                }
            )

        if avg_otif < 0.9:
            signals.append({"type": "otif_pressure", "avg_otif": avg_otif})
        if avg_lead > 25:
            signals.append({"type": "long_lead_times", "avg_lead_time_days": avg_lead})

        return {"summary": summary, "signals": signals}
