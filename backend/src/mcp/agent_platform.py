"""Gemini / Vertex AI platform integration for the agent system.

Provides a single `genai.Client` singleton and an ADK-compatible Gemini
model subclass, both configured for Vertex AI (ADC) auth.
"""

from __future__ import annotations

from functools import cached_property

import google.genai as genai
from google.adk.models.google_llm import Gemini

_genai_client: genai.Client | None = None


def get_genai_client() -> genai.Client:
    """Return a lazily-initialized Gemini API client singleton.

    Configured for Vertex AI (Application Default Credentials) —
    no API key required when running in a Google Cloud environment
    with gcloud auth application-default login.
    """
    global _genai_client  # noqa: PLW0603
    if _genai_client is None:
        _genai_client = genai.Client(vertexai=True)
    return _genai_client


class VertexGemini(Gemini):
    """ADK Gemini model that forces Vertex AI (ADC) auth, not API keys.

    Shares the singleton `genai.Client` from `get_genai_client()` so
    there is exactly one client per process.
    """

    @cached_property
    def api_client(self) -> genai.Client:
        return get_genai_client()
