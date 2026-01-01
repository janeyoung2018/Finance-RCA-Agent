"""
Optional LLM client for decision-support summaries.

Prefers Gemini (free-tier friendly) when GOOGLE_API_KEY is set, otherwise uses
OpenAI chat completions when OPENAI_API_KEY is set. Returns None when neither is
configured so the pipeline stays rule-based with deterministic fallbacks.
"""

import logging
import os
from typing import Callable, Optional

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - dependency optional
    OpenAI = None

try:
    from google import genai
except Exception:  # pragma: no cover - dependency optional
    genai = None

def build_llm() -> Optional[Callable[[str], str]]:
    """
    Build a simple callable that sends a prompt to an LLM and returns the text.

    Order of preference:
    1) Gemini via google-generativeai when GOOGLE_API_KEY is set.
    2) OpenAI chat completions when OPENAI_API_KEY is set.
    Returns None when no API key is configured or the dependency is missing.
    """
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key and genai is not None:
        model_name = os.getenv("LLM_MODEL", "gemini-1.5-flash")
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "256"))
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        client = genai.Client(api_key=google_key)

        def llm(prompt: str) -> str:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    },
                )
                text = getattr(response, "text", None)
                if text:
                    logging.getLogger(__name__).debug("Gemini response.text: %s", text)
                    return text
                # Newer SDKs may use output_text
                text = getattr(response, "output_text", None)
                if text:
                    logging.getLogger(__name__).debug("Gemini output_text: %s", text)
                    return text
                # Fallback: attempt to read from candidates list if present.
                candidates = getattr(response, "candidates", None) or []
                if candidates:
                    first = candidates[0]
                    content = getattr(first, "content", None)
                    if content and getattr(content, "parts", None):
                        part = content.parts[0]
                        # parts may be simple strings or objects with text attr
                        if isinstance(part, str):
                            logging.getLogger(__name__).debug("Gemini candidate part string: %s", part)
                            return part
                        part_text = getattr(part, "text", None)
                        if part_text:
                            logging.getLogger(__name__).debug("Gemini candidate part.text: %s", part_text)
                            return part_text
                    text_field = getattr(first, "text", None)
                    if text_field:
                        logging.getLogger(__name__).debug("Gemini candidate text_field: %s", text_field)
                        return text_field
                return ""
            except Exception as exc:
                logging.getLogger(__name__).warning("Gemini LLM call failed: %s", exc)
                return ""

        return llm

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None

    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "256"))
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    def llm(prompt: str) -> str:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a concise decision-support summarizer."},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content if response.choices else ""
            logging.getLogger(__name__).debug("OpenAI response content: %s", content)
            return content or ""
        except Exception as exc:
            logging.getLogger(__name__).warning("OpenAI LLM call failed: %s", exc)
            return ""

    return llm
