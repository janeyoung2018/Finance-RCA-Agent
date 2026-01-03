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

    def answer(
        self,
        record: RunRecord,
        question: str,
        scope: Optional[str] = None,
        compare_record: Optional[RunRecord] = None,
    ) -> Dict:
        if not record.result:
            raise ValueError("Run has no stored result yet.")

        warnings: List[str] = []
        if record.status != "completed":
            warnings.append(f"Run is {record.status}; results may be partial.")
        if compare_record and compare_record.status != "completed":
            warnings.append(f"Comparison run {compare_record.run_id} is {compare_record.status}; results may be partial.")

        context_sections, sources = self._build_context(record.result, scope)
        if compare_record and compare_record.result:
            compare_sections, compare_sources = self._build_context(compare_record.result, scope, label_prefix="compare")
            context_sections.extend(compare_sections)
            sources.extend([f"compare:{s}" for s in compare_sources])

        if not context_sections:
            raise ValueError("No usable context found for this run.")

        prompt = self._build_prompt(question, context_sections, record.run_id, compare_record.run_id if compare_record else None)
        llm_used = False
        parsed = None

        if self.llm:
            try:
                llm_output = self.llm(prompt)
                if llm_output:
                    parsed = self._parse_structured_answer(llm_output)
                    llm_used = parsed is not None
                    if not parsed:
                        warnings.append("LLM response could not be parsed; using fallback.")
                else:
                    warnings.append("LLM returned an empty response; using fallback.")
            except Exception:
                logging.getLogger(__name__).warning("LLM Q&A call failed; falling back to deterministic answer.", exc_info=True)
                warnings.append("LLM call failed; using deterministic fallback.")
        else:
            warnings.append("LLM is not configured; using deterministic fallback.")

        if parsed:
            answer_text = self._format_parsed_answer(parsed)
            rationale = parsed.get("rationale") or []
            next_questions = parsed.get("next_questions") or []
            evidence_refs = parsed.get("evidence_refs") or sources
            confidence = parsed.get("confidence")
        else:
            answer_text = self._fallback_answer(question, context_sections)
            rationale = []
            next_questions = []
            evidence_refs = sources
            confidence = None

        return {
            "run_id": record.run_id,
            "answer": answer_text,
            "sources": sources,
            "warnings": warnings,
            "llm_used": llm_used,
            "rationale": rationale,
            "next_questions": next_questions,
            "evidence_refs": evidence_refs,
            "confidence": confidence,
        }

    def challenge(self, record: RunRecord, scope: Optional[str] = None) -> Dict:
        """
        Ask the LLM to surface conflicting signals or missing angles.
        """
        if not record.result:
            raise ValueError("Run has no stored result yet.")

        context_sections, sources = self._build_context(record.result, scope)
        prompt = "\n".join(
            [
                "You are an RCA challenge agent.",
                "Using ONLY the provided context, list conflicts, blind spots, or missing checks.",
                "Return JSON with keys: answer (bullets of challenges), rationale, evidence_refs, next_steps.",
                "If none found, say so explicitly.",
                f"Run ID: {record.run_id}",
            ]
            + [f"Context [{sec.get('label','scope')}]: " + " | ".join(sec.get("lines", [])) for sec in context_sections]
            + ["Answer JSON:"]
        )
        warnings: List[str] = []
        parsed = None
        llm_used = False

        if self.llm:
            try:
                raw = self.llm(prompt)
                parsed = self._parse_structured_answer(raw) if raw else None
                llm_used = parsed is not None
            except Exception:
                logging.getLogger(__name__).warning("LLM challenge call failed; using fallback.", exc_info=True)
                warnings.append("LLM call failed; using deterministic fallback.")
        else:
            warnings.append("LLM is not configured; using deterministic fallback.")

        if parsed:
            answer_text = self._format_parsed_answer(parsed)
            rationale = parsed.get("rationale") or []
            next_steps = parsed.get("next_questions") or []
            evidence_refs = parsed.get("evidence_refs") or sources
        else:
            answer_text = "No LLM challenge available; review finance vs demand vs supply for contradictions manually."
            rationale = []
            next_steps = []
            evidence_refs = sources

        return {
            "run_id": record.run_id,
            "answer": answer_text,
            "sources": sources,
            "warnings": warnings,
            "llm_used": llm_used,
            "rationale": rationale,
            "next_questions": next_steps,
            "evidence_refs": evidence_refs,
        }

    def _build_context(self, result: Dict, scope: Optional[str], label_prefix: Optional[str] = None) -> Tuple[List[Dict[str, List[str]]], List[str]]:
        """
        Turn stored RCA outputs into compact text snippets per scope/portfolio.
        """
        sections: List[Dict[str, List[str]]] = []
        sources: List[str] = []

        # Scope-specific (full sweep)
        if scope and result.get("scopes"):
            scope_payload = result["scopes"].get(scope)
            if scope_payload:
                sections.append(self._summarize_scope(scope, scope_payload, label_prefix=label_prefix))
                sources.append(f"{label_prefix + ':' if label_prefix else ''}scope:{scope}")

        # Default to primary result (single-scope or first sweep scope)
        if not sections:
            scope_label = result.get("scope") or scope or "selected scope"
            sections.append(self._summarize_scope(scope_label, result, label_prefix=label_prefix))
            sources.append(f"{label_prefix + ':' if label_prefix else ''}scope:{scope_label}")

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
            label = f"{label_prefix + ':' if label_prefix else ''}portfolio"
            sections.append({"label": label, "lines": lines})
            sources.append(label)

        return sections, sources

    def _summarize_scope(self, label: str, payload: Dict, label_prefix: Optional[str] = None) -> Dict[str, List[str]]:
        lines: List[str] = []
        label_full = f"{label_prefix + ':' if label_prefix else ''}{label}"
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
        top_variances = self._top_variances_from_rollup(rollup)
        for entry in top_variances:
            lines.append(entry)

        domains = payload.get("domains") or {}
        for section_name, entries in [("regions", domains.get("regions") or {}), ("bus", domains.get("bus") or {})]:
            for key, entry in list(entries.items())[:2]:
                if entry.get("summary"):
                    lines.append(f"{section_name} {key}: {entry.get('summary')}")

        return {"label": label_full, "lines": lines}

    def _build_prompt(
        self,
        question: str,
        sections: List[Dict[str, List[str]]],
        run_id: str,
        compare_run_id: Optional[str] = None,
    ) -> str:
        lines = [
            "You are an analyst answering questions using past RCA results.",
            "Use ONLY the provided context. Do not speculate or invent numbers.",
            "If the question is out of scope or unsupported, say you cannot answer from stored results.",
            "Return JSON with keys: answer (list of bullets), rationale (list, optional), sources (list), evidence_refs (list), next_questions (list, optional), confidence (0-1).",
            "Keep answers under 120 words total; do not include markdown formatting.",
            f"Run ID: {run_id}",
        ]
        if compare_run_id:
            lines.append(f"Comparison run: {compare_run_id}")
        for section in sections:
            label = section.get("label", "scope")
            lines.append(f"Context [{label}]:")
            for entry in section.get("lines", []):
                lines.append(f"- {entry}")
        lines.append(f"Question: {question}")
        lines.append("Answer JSON:")
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

    def _top_variances_from_rollup(self, rollup: Dict, limit: int = 3) -> List[str]:
        """
        Extract top absolute variances from rollup metrics to steer context toward most material drivers.
        """
        if not rollup:
            return []
        overall = (rollup.get("overall") or {}).get("metrics") or {}
        scored = []
        for metric, values in overall.items():
            var_plan = values.get("variance_to_plan")
            var_prior = values.get("variance_to_prior")
            # Use whichever variance has magnitude
            best_var = None
            if var_plan is not None and var_prior is not None:
                best_var = var_plan if abs(var_plan) >= abs(var_prior) else var_prior
            else:
                best_var = var_plan if var_plan is not None else var_prior
            if best_var is not None:
                scored.append((metric, best_var, values))
        scored = sorted(scored, key=lambda x: abs(x[1]), reverse=True)[:limit]
        lines: List[str] = []
        for metric, variance, values in scored:
            lines.append(
                f"{metric}: variance {variance} (plan {values.get('plan')}, prior {values.get('prior')}, actual {values.get('actual')})"
            )
        return lines

    def _parse_structured_answer(self, text: str) -> Optional[Dict]:
        """
        Attempt to parse the LLM output as JSON and normalize fields.
        """
        cleaned = text.strip()
        try:
            data = json.loads(cleaned)
            if not isinstance(data, dict):
                return None
            answer = data.get("answer")
            if isinstance(answer, str):
                answer = [answer]
            if not isinstance(answer, list):
                return None
            rationale = data.get("rationale")
            if isinstance(rationale, str):
                rationale = [rationale]
            if rationale is None:
                rationale = []
            if not isinstance(rationale, list):
                rationale = []
            sources = data.get("sources") or []
            if isinstance(sources, str):
                sources = [sources]
            if not isinstance(sources, list):
                sources = []
            next_questions = data.get("next_questions") or []
            if isinstance(next_questions, str):
                next_questions = [next_questions]
            if not isinstance(next_questions, list):
                next_questions = []
            evidence_refs = data.get("evidence_refs") or []
            if isinstance(evidence_refs, str):
                evidence_refs = [evidence_refs]
            if not isinstance(evidence_refs, list):
                evidence_refs = []
            confidence = data.get("confidence")
            try:
                confidence_val = float(confidence) if confidence is not None else None
            except Exception:
                confidence_val = None
            return {
                "answer": [self._normalize(line) for line in answer if isinstance(line, str)],
                "rationale": [self._normalize(line) for line in rationale if isinstance(line, str)],
                "sources": [self._normalize(line) for line in sources if isinstance(line, str)],
                "next_questions": [self._normalize(line) for line in next_questions if isinstance(line, str)],
                "evidence_refs": [self._normalize(line) for line in evidence_refs if isinstance(line, str)],
                "confidence": confidence_val,
            }
        except Exception:
            return None

    def _format_parsed_answer(self, parsed: Dict) -> str:
        """
        Flatten the structured response to a user-friendly string while keeping bullets concise.
        """
        answer_lines = parsed.get("answer") or []
        rationale = parsed.get("rationale") or []
        next_questions = parsed.get("next_questions") or []

        parts: List[str] = []
        for line in answer_lines:
            parts.append(f"- {line}")
        if rationale:
            parts.append("Rationale:")
            for line in rationale:
                parts.append(f"- {line}")
        if next_questions:
            parts.append("Next questions:")
            for line in next_questions:
                parts.append(f"- {line}")
        return "\n".join(parts)

    def _normalize(self, text: str) -> str:
        return text.replace("*", "").strip()
