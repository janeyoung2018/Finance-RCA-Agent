from typing import Dict, List

import pandas as pd

from src.tools.variance import filter_by_scope


class DemandAgent:
    def analyze(self, df: pd.DataFrame, month: str, **filters) -> Dict:
        scoped = filter_by_scope(df, month, **filters)
        if scoped.empty:
            return {"summary": "No demand data for scope.", "signals": []}

        summary_parts: List[str] = []
        signals: List[Dict] = []

        orders_total = scoped["orders"].sum()
        cancels = scoped["cancellations"].sum()
        avg_discount = scoped["avg_discount"].mean()
        asp = scoped["asp"].mean()
        summary_parts.append(f"Orders {orders_total:,.0f}, cancels {cancels:,.0f}, avg discount {avg_discount:.2f}, ASP {asp:,.0f}.")

        # Compare to prior month if available
        try:
            import pandas as pd
            prior_month = (pd.Period(month) - 1).strftime("%Y-%m")
        except Exception:
            prior_month = None

        if prior_month:
            prior_scoped = filter_by_scope(df, prior_month, **filters)
            if not prior_scoped.empty:
                prev_orders = prior_scoped["orders"].sum()
                delta = orders_total - prev_orders
                signals.append(
                    {
                        "type": "orders_change",
                        "current": orders_total,
                        "prior": prev_orders,
                        "delta": delta,
                        "month_compare": f"{prior_month} -> {month}",
                    }
                )

        # Flag high discounting
        if avg_discount >= 0.25:
            signals.append({"type": "high_discounting", "avg_discount": avg_discount})

        return {"summary": " ".join(summary_parts), "signals": signals}
