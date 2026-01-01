import logging
import os
from pathlib import Path

import pytest

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None

if load_dotenv:
    load_dotenv(dotenv_path=Path(".env"), override=False)


def test_gemini_live_round_trip(caplog):
    """Simple live check that the configured Gemini API key can return text."""
    from google import genai

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not set; live Gemini test skipped.")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=os.getenv("LLM_MODEL", "gemini-2.5-flash-lite"),
        contents="Return the word 'pong' only.",
        config={"max_output_tokens": 8, "temperature": 0.0},
    )

    text = getattr(response, "text", "") or ""
    caplog.set_level("INFO")
    logging.getLogger(__name__).info("Gemini response: %s", text)
    assert "pong" in text.lower()
