from typing import Dict, List

import pandas as pd

from src.tools.variance import filter_by_scope


class EventsAgent:
    def analyze(self, df: pd.DataFrame, month: str, **filters) -> Dict:
        scoped = filter_by_scope(df, month, **filters)
        if scoped.empty:
            return {"summary": "No events logged for scope.", "events": []}

        events: List[Dict] = []
        for _, row in scoped.iterrows():
            events.append(
                {
                    "date": row.get("date"),
                    "type": row.get("type"),
                    "summary": row.get("summary"),
                    "region": row.get("region"),
                    "bu": row.get("bu"),
                    "product_line": row.get("product_line"),
                }
            )

        summary = f"{len(events)} events in month."
        return {"summary": summary, "events": events}
