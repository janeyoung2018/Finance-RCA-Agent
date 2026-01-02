from collections import Counter
from typing import Callable, Dict, List, Optional
import logging


class SynthesisAgent:
    def __init__(self, llm: Optional[Callable[[str], str]] = None) -> None:
        """
        Optionally accept an LLM callable that takes a prompt and returns text.

        When not provided, falls back to a deterministic decision-support stub.
        """
        self.llm = llm

    def synthesize(
        self,
        finance: Dict,
        demand: Dict,
        supply: Dict,
        shipments: Dict,
        fx: Dict,
        events: Dict,
        scope_label: Optional[str] = None,
        filters: Optional[Dict[str, str]] = None,
        month: Optional[str] = None,
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

        rule_summary = " | ".join(summary_parts) if summary_parts else "No findings."
        brief_report = self._compose_brief(scope_label or "selected scope", finance, demand, supply, shipments, fx, events)
        decision_summary = self._llm_decision_support(
            rule_summary,
            brief_report,
            finance,
            demand,
            supply,
            shipments,
            fx,
            events,
            filters,
            scope_label,
            month,
        )

        return {
            "summary": rule_summary,  # preserved for compatibility
            "rule_summary": rule_summary,
            "findings": findings,
            "brief_report": brief_report,
            "llm_decision_summary": decision_summary,
        }

    def summarize_sweep(self, scope_results: Dict[str, Dict], base_filters: Optional[Dict[str, str]] = None, month: Optional[str] = None) -> Dict:
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
        decision_summary = self._llm_decision_support_portfolio(portfolio_brief, top_hotspots, scope_results, base_filters, month)
        return {
            "portfolio_brief": portfolio_brief,
            "rule_portfolio_brief": portfolio_brief,
            "hotspots": top_hotspots,
            "llm_decision_summary": decision_summary,
        }

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

    def _llm_decision_support(
        self,
        rule_summary: str,
        brief_report: str,
        finance: Dict,
        demand: Dict,
        supply: Dict,
        shipments: Dict,
        fx: Dict,
        events: Dict,
        filters: Optional[Dict[str, str]],
        scope_label: Optional[str],
        month: Optional[str],
    ) -> str:
        prompt = self._decision_support_prompt(
            rule_summary,
            brief_report,
            finance,
            demand,
            supply,
            shipments,
            fx,
            events,
            filters,
            scope_label,
            month,
        )
        if self.llm:
            try:
                llm_result = self.llm(prompt)
                if llm_result:
                    logging.getLogger(__name__).debug("Scope LLM decision summary produced.")
                    return self._normalize_llm_text(llm_result)
                logging.getLogger(__name__).info("Scope LLM returned empty response; using fallback.")
            except Exception:
                # Fall back if the LLM call fails to keep workflow deterministic.
                logging.getLogger(__name__).warning("Scope LLM call failed; using fallback.", exc_info=True)
                pass
        return self._fallback_decision_brief(finance, demand, supply, shipments, fx, events, rule_summary, filters, scope_label, month)

    def _llm_decision_support_portfolio(
        self,
        portfolio_brief: str,
        hotspots: List[Dict],
        scope_results: Dict[str, Dict],
        base_filters: Optional[Dict[str, str]],
        month: Optional[str],
    ) -> str:
        prompt = self._portfolio_decision_prompt(portfolio_brief, hotspots, base_filters, month)
        if self.llm:
            try:
                llm_result = self.llm(prompt)
                if llm_result:
                    logging.getLogger(__name__).debug("Portfolio LLM decision summary produced.")
                    return self._normalize_llm_text(llm_result)
                logging.getLogger(__name__).info("Portfolio LLM returned empty response; using fallback.")
            except Exception:
                logging.getLogger(__name__).warning("Portfolio LLM call failed; using fallback.", exc_info=True)
                pass
        return self._fallback_portfolio_brief(portfolio_brief, hotspots, scope_results, base_filters, month)

    def _decision_support_prompt(
        self,
        rule_summary: str,
        brief_report: str,
        finance: Dict,
        demand: Dict,
        supply: Dict,
        shipments: Dict,
        fx: Dict,
        events: Dict,
        filters: Optional[Dict[str, str]],
        scope_label: Optional[str],
        month: Optional[str],
    ) -> str:
        """
        Compact prompt to steer an LLM toward decision-support (not raw restatement).
        """
        filter_line = self._format_filters(filters, month)
        comparison = finance.get("comparison") or "plan"
        lines = [
            "You are a finance RCA decision-support agent writing for finance leads.",
            "Anchor on the selected scope and filters; avoid generic advice.",
            "Return 3-5 short lines prefixed with '-' (no markdown emphasis or asterisks).",
            f"Scope: {scope_label or 'selected scope'} | Filters: {filter_line} | Comparison: {comparison}",
            f"Rule summary: {rule_summary}",
            f"Brief narrative: {brief_report}",
            f"Finance drivers: {self._format_top_driver(finance) or 'none'}",
            f"Demand signals: {self._format_signal_counts(demand.get('signals'))}",
            f"Supply signals: {self._format_signal_counts(supply.get('signals'))}",
            f"Shipments signals: {self._format_signal_counts(shipments.get('signals'))}",
            f"FX signals: {self._format_signal_counts(fx.get('signals'))}",
            f"Events: {len(events.get('events') or [])}",
            "Focus on implications (why it moved, what to watch, next action owners).",
        ]
        return "\n".join(lines)

    def _portfolio_decision_prompt(self, portfolio_brief: str, hotspots: List[Dict], base_filters: Optional[Dict[str, str]], month: Optional[str]) -> str:
        return "\n".join(
            [
                "You are summarizing a multi-scope RCA sweep for executives.",
                "Deliver decision-ready insights, themes, and top follow-ups in <=120 words.",
                "Return 3-5 short lines prefixed with '-' (no markdown emphasis or asterisks).",
                f"Month: {month or 'unspecified'} | Base filters: {self._format_filters(base_filters, None)}",
                f"Rule-based portfolio brief: {portfolio_brief}",
                f"Hotspots by domain: {hotspots}",
            ]
        )

    def _fallback_decision_brief(
        self,
        finance: Dict,
        demand: Dict,
        supply: Dict,
        shipments: Dict,
        fx: Dict,
        events: Dict,
        rule_summary: str,
        filters: Optional[Dict[str, str]],
        scope_label: Optional[str],
        month: Optional[str],
    ) -> str:
        driver = self._format_top_driver(finance)
        ops_signals = self._format_ops_signals(demand, supply, shipments, fx)
        events_count = len(events.get("events") or [])
        scope_context = self._format_filters(filters, month)

        risks: List[str] = []
        if not ops_signals:
            risks.append("Sparse operational signals; validate data freshness")
        if events_count > 0:
            risks.append("Contextual events may be confounding the variance")

        actions: List[str] = []
        if demand.get("signals"):
            actions.append("Validate promo/discount levers vs demand drop")
        if supply.get("signals"):
            actions.append("Escalate OTIF/lead-time fixes with suppliers")
        if shipments.get("signals"):
            actions.append("Stabilize fulfillment and reroute inventory where lagging")
        if fx.get("signals"):
            actions.append("Review hedges/pricing for FX-sensitive regions")

        parts: List[str] = []
        parts.append(f"- Scope: {scope_label or 'selected scope'} | Filters: {scope_context}")
        parts.append(f"- Reference: {rule_summary}")
        if driver:
            parts.append(f"- Primary driver: {driver}.")
        if ops_signals:
            parts.append(f"- Ops signals: {ops_signals}.")
        if events_count:
            parts.append(f"- Events to factor: {events_count} recorded.")
        if risks:
            parts.append(f"- Risks: {', '.join(risks)}.")
        if actions:
            parts.append(f"- Next actions: {', '.join(actions)}.")
        return "\n".join(parts)

    def _fallback_portfolio_brief(self, portfolio_brief: str, hotspots: List[Dict], scope_results: Dict[str, Dict], base_filters: Optional[Dict[str, str]], month: Optional[str]) -> str:
        themes = ", ".join([f"{h['domain']} x{h['occurrences']}" for h in hotspots]) if hotspots else "No dominant hotspots"
        scope_count = len(scope_results)
        filters_line = self._format_filters(base_filters, month)
        return "\n".join(
            [
                f"- Month: {month or 'unspecified'} | Filters: {filters_line}",
                f"- Reference sweep: {portfolio_brief}",
                f"- Themes: {themes}.",
                f"- Coverage: {scope_count} scopes processed.",
            ]
        )

    def _format_top_driver(self, finance: Dict) -> Optional[str]:
        top = finance.get("top_contributors") or []
        if not top:
            return None
        lead = top[0]
        metric = lead.get("metric")
        variance = lead.get("variance") or lead.get("variance_to_plan") or lead.get("variance_to_prior")
        parts = []
        if metric:
            parts.append(str(metric))
        if variance is not None:
            try:
                parts.append(f"{variance:,.0f} variance")
            except Exception:
                parts.append(f"variance {variance}")
        for key in ["region", "bu", "product_line", "segment"]:
            if lead.get(key):
                parts.append(f"{key} {lead[key]}")
        return " | ".join(parts) if parts else None

    def _format_signal_counts(self, signals: Optional[List[Dict]]) -> str:
        if not signals:
            return "none"
        counts = Counter(sig.get("type", "unknown") for sig in signals)
        return ", ".join([f"{k} x{v}" for k, v in counts.most_common()])

    def _format_ops_signals(self, demand: Dict, supply: Dict, shipments: Dict, fx: Dict) -> str:
        sections = []
        for title, payload in [
            ("demand", demand.get("signals")),
            ("supply", supply.get("signals")),
            ("shipments", shipments.get("signals")),
            ("fx", fx.get("signals")),
        ]:
            if payload:
                sections.append(f"{title}:{self._format_signal_counts(payload)}")
        return "; ".join(sections)

    def _format_filters(self, filters: Optional[Dict[str, str]], month: Optional[str]) -> str:
        if not filters and not month:
            return "none"
        entries: List[str] = []
        if month:
            entries.append(f"month={month}")
        for key in ["region", "bu", "product_line", "segment", "metric", "comparison"]:
            value = (filters or {}).get(key)
            if value:
                entries.append(f"{key}={value}")
        return ", ".join(entries) if entries else "unfiltered"

    def _normalize_llm_text(self, text: str) -> str:
        if not text:
            return ""
        cleaned = text.replace("**", "")
        return "\n".join([line.strip() for line in cleaned.splitlines() if line.strip()])
