from typing import Dict, List

import pandas as pd

from src.tools.variance import filter_by_scope


class ShipmentsAgent:
    def analyze(self, df: pd.DataFrame, month: str, **filters) -> Dict:
        scoped = filter_by_scope(df, month, **filters)
        if scoped.empty:
            return {"summary": "No shipments data for scope.", "signals": []}

        signals: List[Dict] = []
        avg_fulfillment = scoped["fulfillment_rate"].mean()
        total_shipped = scoped["shipped_units"].sum()
        summary = f"Fulfillment {avg_fulfillment:.2f}, shipped units {total_shipped:,.0f}."

        # Flag low fulfillment slices
        low = scoped[scoped["fulfillment_rate"] < 0.9].sort_values("fulfillment_rate").head(5)
        for _, row in low.iterrows():
            signals.append(
                {
                    "type": "low_fulfillment",
                    "fulfillment_rate": row["fulfillment_rate"],
                    "region": row.get("region"),
                    "bu": row.get("bu"),
                    "product_line": row.get("product_line"),
                }
            )

        return {"summary": summary, "signals": signals}
