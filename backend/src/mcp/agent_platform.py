"""LLM provider for the Canon agent system.

Default is Gemini on Vertex AI, authenticated via Application Default
Credentials (ADC). Setting both ``CANON_LLM_API_KEY`` and
``CANON_LLM_API_BASE`` switches to a remote model via ADK's
provider abstraction.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any

import google.genai as genai
import httpx
from google.adk.models.google_llm import Gemini
from google.adk.models.lite_llm import LiteLlm

from src.config import settings

# ─── Vertex AI (default) ─────────────────────────────────────────────────────


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


# ─── Public API ──────────────────────────────────────────────────────────────


class CanonModel:
    """Factory for ADK-compatible model instances and GenAI clients.

    Gemini on Vertex AI via ADC by default — no API key needed.
    When both ``CANON_LLM_API_KEY`` and ``CANON_LLM_API_BASE`` are set,
    a remote model provider is used instead.
    """

    @staticmethod
    def create(model_name: str) -> Any:
        """Return an ADK-compatible model for ``Agent(model=...)``."""
        if settings.llm_api_key and settings.llm_api_base:
            return LiteLlm(
                model=model_name,
                api_key=settings.llm_api_key,
                api_base=settings.llm_api_base,
            )
        return VertexGemini(model=model_name)

    @staticmethod
    async def generate_text(model_name: str, prompt: str) -> str | None:
        """Generate text directly (no agent). Returns ``None`` if no text produced.

        Uses Vertex AI by default, or the remote provider's
        ``/v1/chat/completions`` endpoint when API key + base are configured.
        """
        if settings.llm_api_key and settings.llm_api_base:
            return await CanonModel._generate_text_remote(model_name, prompt)
        return await CanonModel._generate_text_vertexai(model_name, prompt)

    @staticmethod
    async def _generate_text_vertexai(model_name: str, prompt: str) -> str | None:
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
            return None
        return result.text.strip()

    @staticmethod
    async def _generate_text_remote(model_name: str, prompt: str) -> str | None:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.llm_api_base}/chat/completions",
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 512,
                },
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                return None
            return choices[0]["message"]["content"].strip()

    @staticmethod
    async def embed(text: str, *, task_type: str, model: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Uses Vertex AI by default, or the remote provider's
        ``/v1/embeddings`` endpoint when API key + base are configured.
        """
        if settings.llm_api_key and settings.llm_api_base:
            return await CanonModel._embed_remote(text, model=model)
        return await CanonModel._embed_vertexai(text, task_type=task_type, model=model)

    @staticmethod
    async def _embed_vertexai(text: str, *, task_type: str, model: str) -> list[float]:
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

    @staticmethod
    async def _embed_remote(text: str, *, model: str) -> list[float]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.llm_api_base}/embeddings",
                json={
                    "model": model,
                    "input": text,
                    "encoding_format": "float",
                },
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("data", [])
            if not embeddings:
                raise RuntimeError("Embedding API returned empty response.")
            return embeddings[0]["embedding"]
