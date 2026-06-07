from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

from openai import OpenAI, OpenAIError

from common.openai_response import response_field


class EmbeddingError(RuntimeError):
    pass


class EmbeddingClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 30,
        retries: int = 3,
        text_limit: int = 16000,
        client: Any | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.text_limit = text_limit
        self._owns_client = client is None
        self._client = client or OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=timeout_seconds,
            max_retries=0,
        )

    def close(self) -> None:
        if self._owns_client and hasattr(self._client, "close"):
            self._client.close()

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "model": self.model,
            "input": [self._limit_text(text) for text in texts],
        }
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self._client.embeddings.create(**payload)
                return self._parse_response(response, expected_count=len(texts))
            except (OpenAIError, EmbeddingError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
                status_code = getattr(exc, "status_code", None)
                if status_code is not None and status_code < 500:
                    break
                if attempt < self.retries:
                    time.sleep(min(2 ** (attempt - 1), 4))
        raise EmbeddingError(f"embedding endpoint unavailable or returned invalid data: {last_error}") from last_error

    def _limit_text(self, text: str) -> str:
        if len(text) <= self.text_limit:
            return text
        return text[: self.text_limit]

    @staticmethod
    def _parse_response(data: Any, expected_count: int) -> list[list[float]]:
        rows = response_field(data, "data")
        if len(rows) != expected_count:
            raise EmbeddingError(f"expected {expected_count} embeddings, got {len(rows)}")
        if all(response_field(row, "index", None) is not None for row in rows):
            rows = sorted(rows, key=lambda row: response_field(row, "index"))
        vectors = [response_field(row, "embedding") for row in rows]
        if not all(isinstance(vector, list) and vector for vector in vectors):
            raise EmbeddingError("embedding response contains empty or invalid vectors")
        return vectors
