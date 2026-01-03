"""
LLM-backed reasoning endpoint for ad-hoc Q&A over completed RCA runs.

Relies solely on stored run outputs (synthesis, rollups, domains) and never
touches raw tables. Falls back to deterministic summaries when no LLM is
configured or a call fails.
"""

import json
import logging
from typing import Callable, Dict, List, Optional, Tuple

from src.llm.client import build_llm
from src.memory.run_store import RunRecord


class LLMReasoner:
    def __init__(self, llm: Optional[Callable[[str], str]] = None) -> None:
        self.llm = llm if llm is not None else build_llm()

    def answer(self, record: RunRecord, question: str, scope: Optional[str] = None) -> Dict:
        if not record.result:
            raise ValueError("Run has no stored result yet.")

        warnings: List[str] = []
        if record.status != "completed":
            warnings.append(f"Run is {record.status}; results may be partial.")

        context_sections, sources = self._build_context(record.result, scope)
        if not context_sections:
            raise ValueError("No usable context found for this run.")

        prompt = self._build_prompt(question, context_sections, record.run_id)
        llm_used = False
        answer_text = ""

        if self.llm:
            try:
                llm_output = self.llm(prompt)
                if llm_output:
                    answer_text = self._normalize(llm_output)
                    llm_used = True
                else:
                    warnings.append("LLM returned an empty response; using fallback.")
            except Exception:
                logging.getLogger(__name__).warning("LLM Q&A call failed; falling back to deterministic answer.", exc_info=True)
                warnings.append("LLM call failed; using deterministic fallback.")
        else:
            warnings.append("LLM is not configured; using deterministic fallback.")

        if not answer_text:
            answer_text = self._fallback_answer(question, context_sections)

        return {
            "run_id": record.run_id,
            "answer": answer_text,
            "sources": sources,
            "warnings": warnings,
            "llm_used": llm_used,
        }

    def _build_context(self, result: Dict, scope: Optional[str]) -> Tuple[List[Dict[str, List[str]]], List[str]]:
        """
        Turn stored RCA outputs into compact text snippets per scope/portfolio.
        """
        sections: List[Dict[str, List[str]]] = []
        sources: List[str] = []

        # Scope-specific (full sweep)
        if scope and result.get("scopes"):
            scope_payload = result["scopes"].get(scope)
            if scope_payload:
                sections.append(self._summarize_scope(scope, scope_payload))
                sources.append(f"scope:{scope}")

        # Default to primary result (single-scope or first sweep scope)
        if not sections:
            scope_label = result.get("scope") or scope or "selected scope"
            sections.append(self._summarize_scope(scope_label, result))
            sources.append(f"scope:{scope_label}")

        # Portfolio sweep context
        if result.get("portfolio"):
            portfolio = result["portfolio"]
            lines: List[str] = []
            brief = portfolio.get("portfolio_brief") or portfolio.get("rule_portfolio_brief")
            if brief:
                lines.append(f"Portfolio brief: {brief}")
            hotspots = portfolio.get("hotspots") or []
            if hotspots:
                top_hotspots = ", ".join([f"{h.get('domain')}: {h.get('occurrences')}" for h in hotspots[:5]])
                lines.append(f"Hotspots: {top_hotspots}")
            decision = portfolio.get("llm_decision_summary")
            if decision:
                lines.append(f"LLM sweep summary: {self._normalize(decision)}")
            sections.append({"label": "portfolio", "lines": lines})
            sources.append("portfolio")

        return sections, sources

    def _summarize_scope(self, label: str, payload: Dict) -> Dict[str, List[str]]:
        lines: List[str] = []
        filters = payload.get("filters") or {}
        if filters:
            lines.append(f"Filters: {json.dumps(filters, sort_keys=True)}")

        synthesis = payload.get("synthesis") or {}
        rule_summary = synthesis.get("rule_summary") or synthesis.get("summary")
        if rule_summary:
            lines.append(f"Rule summary: {rule_summary}")
        brief = synthesis.get("brief_report")
        if brief:
            lines.append(f"Brief: {brief}")
        decision = synthesis.get("llm_decision_summary")
        if decision:
            lines.append(f"LLM summary: {self._normalize(decision)}")

        rollup = payload.get("rollup") or {}
        overall = (rollup.get("overall") or {}).get("metrics") or {}
        if overall:
            for metric, values in list(overall.items())[:3]:
                var_plan = values.get("variance_to_plan")
                var_prior = values.get("variance_to_prior")
                lines.append(
                    f"{metric}: actual {values.get('actual')}, var vs plan {var_plan}, var vs prior {var_prior}"
                )

        domains = payload.get("domains") or {}
        for section_name, entries in [("regions", domains.get("regions") or {}), ("bus", domains.get("bus") or {})]:
            for key, entry in list(entries.items())[:2]:
                if entry.get("summary"):
                    lines.append(f"{section_name} {key}: {entry.get('summary')}")

        return {"label": label, "lines": lines}

    def _build_prompt(self, question: str, sections: List[Dict[str, List[str]]], run_id: str) -> str:
        lines = [
            "You are an analyst answering questions using past RCA results.",
            "Use ONLY the provided context. Do not speculate or invent numbers.",
            "If the question is out of scope, say you cannot answer from stored results.",
            "Return concise bullet lines (prefix with '-') and keep under 120 words.",
            f"Run ID: {run_id}",
        ]
        for section in sections:
            label = section.get("label", "scope")
            lines.append(f"Context [{label}]:")
            for entry in section.get("lines", []):
                lines.append(f"- {entry}")
        lines.append(f"Question: {question}")
        lines.append("Answer:")
        return "\n".join(lines)

    def _fallback_answer(self, question: str, sections: List[Dict[str, List[str]]]) -> str:
        top_lines: List[str] = []
        for section in sections:
            for line in section.get("lines", [])[:3]:
                top_lines.append(line)
            if len(top_lines) >= 6:
                break
        if not top_lines:
            return "No stored findings available to answer this question yet."
        return "Deterministic summary (no LLM available): " + " ".join(top_lines) + f" | Question: {question}"

    def _normalize(self, text: str) -> str:
        return text.replace("*", "").strip()
