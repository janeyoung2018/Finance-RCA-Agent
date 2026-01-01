from collections import Counter
from typing import Dict, List, Optional


class SynthesisAgent:
    def synthesize(
        self,
        finance: Dict,
        demand: Dict,
        supply: Dict,
        shipments: Dict,
        fx: Dict,
        events: Dict,
        scope_label: Optional[str] = None,
    ) -> Dict:
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
        brief_report = self._compose_brief(scope_label or "selected scope", finance, demand, supply, shipments, fx, events)
        return {"summary": summary, "findings": findings, "brief_report": brief_report}

    def summarize_sweep(self, scope_results: Dict[str, Dict]) -> Dict:
        """
        Create a portfolio-level overview across multiple scope syntheses.
        """
        hotspots = Counter()
        scope_summaries: List[str] = []

        for label, payload in scope_results.items():
            synthesis = payload.get("synthesis", {})
            summary = synthesis.get("summary") or "No summary."
            scope_summaries.append(f"{label}: {summary}")
            for finding in synthesis.get("findings", []):
                domain = finding.get("domain", "unknown")
                hotspots[domain] += 1

        top_hotspots = [{"domain": domain, "occurrences": count} for domain, count in hotspots.most_common()]
        portfolio_brief = " ".join(scope_summaries) if scope_summaries else "No completed scopes."
        return {"portfolio_brief": portfolio_brief, "hotspots": top_hotspots}

    def _compose_brief(self, scope_label: str, finance: Dict, demand: Dict, supply: Dict, shipments: Dict, fx: Dict, events: Dict) -> str:
        """
        Lightweight narrative intended for stakeholder consumption.
        """
        lines: List[str] = [f"Scope: {scope_label}."]

        finance_summary = finance.get("summary") or "No finance variance found."
        lines.append(f"Finance: {finance_summary}")
        contributors = finance.get("top_contributors") or []
        if contributors:
            lead = contributors[0]
            parts = [f"{lead.get('metric')}: {lead.get('variance', 0):,.0f}"]
            if lead.get("region"):
                parts.append(f"region {lead['region']}")
            if lead.get("bu"):
                parts.append(f"BU {lead['bu']}")
            lines.append(f"Primary driver: {' | '.join(parts)}.")

        signals_sections = [
            ("Demand", demand.get("signals")),
            ("Supply", supply.get("signals")),
            ("Shipments", shipments.get("signals")),
            ("FX", fx.get("signals")),
            ("Events", events.get("events")),
        ]

        for title, signals in signals_sections:
            if signals:
                kinds = Counter(signal.get("type", "unknown") for signal in signals)
                formatted = ", ".join([f"{k} x{v}" for k, v in kinds.most_common()])
                lines.append(f"{title}: {formatted}.")

        if not any(section[1] for section in signals_sections):
            lines.append("No operational signals detected across demand, supply, shipments, FX, or events.")

        return " ".join(lines)
