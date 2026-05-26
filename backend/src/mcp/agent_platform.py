"""LLM provider for the Canon agent system.

Gemini on Vertex AI, authenticated via Application Default
Credentials (ADC).
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


class VertexGemini(Gemini):
    """ADK Gemini model that forces Vertex AI (ADC) auth, not API keys."""

    @cached_property
    def api_client(self) -> genai.Client:
        return _GenaiClient.get()


class CanonModel:
    """Factory for ADK-compatible model instances and GenAI clients.

    Gemini on Vertex AI via ADC — no API key needed.
    """

    @staticmethod
    def create(model_name: str) -> VertexGemini:
        """Return an ADK-compatible model for ``Agent(model=...)``."""
        return VertexGemini(model=model_name)

    @staticmethod
    async def generate_text(model_name: str, prompt: str) -> str:
        """Generate text directly (no agent)."""
        from google.genai import types

        client = _GenaiClient.get()
        result = await client.aio.models.generate_content(
            model=f"models/{model_name}",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=512,
            ),
        )
        if not result.text:
            return ""
        return result.text.strip()

    @staticmethod
    async def embed(text: str, *, task_type: str, model: str) -> list[float]:
        """Generate an embedding vector."""
        from google.genai import types

        client = _GenaiClient.get()
        response = await client.aio.models.embed_content(
            model=model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=768,
            ),
        )
        if not response.embeddings:
            raise RuntimeError("Embedding API returned empty response.")
        values = response.embeddings[0].values
        if values is None:
            raise RuntimeError("Embedding API returned None values.")
        return values
