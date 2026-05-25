"""Gemini / Vertex AI platform integration for the agent system.

Provides a single `genai.Client` singleton and an ADK-compatible Gemini
model subclass, both configured for Vertex AI (ADC) auth.
"""

from __future__ import annotations

from functools import cached_property

import google.genai as genai
from google.adk.models.google_llm import Gemini


class _GenaiClient:
    """Module-level singleton container for the Vertex AI client."""

    _instance: genai.Client | None = None

    @classmethod
    def get(cls) -> genai.Client:
        if cls._instance is None:
            cls._instance = genai.Client(vertexai=True)
        return cls._instance


def get_genai_client() -> genai.Client:
    """Return a shared Vertex AI Gemini API client singleton.

    Configured for Application Default Credentials — no API key
    required when running in a Google Cloud environment with
    ``gcloud auth application-default login``.
    """
    return _GenaiClient.get()


class VertexGemini(Gemini):
    """ADK Gemini model that forces Vertex AI (ADC) auth, not API keys.

    Shares the singleton ``genai.Client`` via ``_GenaiClient`` so there
    is exactly one client per process.
    """

    @cached_property
    def api_client(self) -> genai.Client:
        return _GenaiClient.get()
