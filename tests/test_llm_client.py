import os

import pytest

from src.llm import client


def test_build_llm_returns_none_without_keys(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Ensure both providers appear unavailable.
    monkeypatch.setattr(client, "genai", None, raising=False)
    monkeypatch.setattr(client, "OpenAI", None, raising=False)

    llm = client.build_llm()

    assert llm is None


def test_build_llm_uses_gemini_when_configured(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-1.5-flash")
    monkeypatch.setenv("LLM_MAX_TOKENS", "16")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    class StubResponse:
        def __init__(self, text: str) -> None:
            self.text = text

    class StubModels:
        def __init__(self):
            self.calls = []

        def generate_content(self, **kwargs):
            self.calls.append(kwargs)
            return StubResponse("stub-output")

    class StubClient:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.models = StubModels()

    stub_genai_module = type("StubGenai", (), {"Client": StubClient})
    monkeypatch.setattr(client, "genai", stub_genai_module, raising=False)
    monkeypatch.setattr(client, "OpenAI", None, raising=False)  # force Gemini path

    llm = client.build_llm()
    assert llm is not None

    output = llm("hello world")
    assert output == "stub-output"


def test_build_llm_falls_back_to_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_MAX_TOKENS", "8")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.0")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    class StubChoice:
        def __init__(self, content: str) -> None:
            self.message = type("Msg", (), {"content": content})

    class StubResponse:
        def __init__(self, content: str) -> None:
            self.choices = [StubChoice(content)]

    class StubChat:
        def __init__(self):
            self.completions = self
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return StubResponse("openai-output")

    class StubClient:
        def __init__(self, api_key=None, base_url=None):
            self.api_key = api_key
            self.base_url = base_url
            self.chat = StubChat()

    monkeypatch.setattr(client, "genai", None, raising=False)  # force OpenAI path
    monkeypatch.setattr(client, "OpenAI", StubClient, raising=False)

    llm = client.build_llm()
    assert llm is not None

    output = llm("prompt")
    assert output == "openai-output"
