from typing import Dict, List


class SynthesisAgent:
    def synthesize(self, finance: Dict, demand: Dict, supply: Dict, shipments: Dict, fx: Dict, events: Dict) -> Dict:
        summary_parts: List[str] = []
        findings: List[Dict] = []

        if finance.get("summary"):
            summary_parts.append(f"Finance: {finance['summary']}")
            findings.append({"domain": "finance", "detail": finance})

        if demand.get("signals"):
            summary_parts.append("Demand signals present.")
            findings.append({"domain": "demand", "detail": demand})

        if supply.get("signals"):
            summary_parts.append("Supply constraints detected.")
            findings.append({"domain": "supply", "detail": supply})

        if shipments.get("signals"):
            summary_parts.append("Fulfillment issues detected.")
            findings.append({"domain": "shipments", "detail": shipments})

        if fx.get("signals"):
            summary_parts.append("FX movements noted.")
            findings.append({"domain": "fx", "detail": fx})

        if events.get("events"):
            summary_parts.append("Contextual events noted.")
            findings.append({"domain": "events", "detail": events})

        summary = " | ".join(summary_parts) if summary_parts else "No findings."
        return {"summary": summary, "findings": findings}
