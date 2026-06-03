from __future__ import annotations

import time
from collections.abc import Sequence

import httpx


class EmbeddingError(RuntimeError):
    pass


class EmbeddingClient:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: int = 30,
        retries: int = 3,
        text_limit: int = 16000,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.text_limit = text_limit
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        if self._owns_client:
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
                response = self._client.post(f"{self.base_url}/embeddings", json=payload)
                if response.status_code >= 500:
                    raise EmbeddingError(f"embedding endpoint returned HTTP {response.status_code}")
                response.raise_for_status()
                return self._parse_response(response.json(), expected_count=len(texts))
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError, EmbeddingError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                    break
                if attempt < self.retries:
                    time.sleep(min(2 ** (attempt - 1), 4))
        raise EmbeddingError(f"embedding endpoint unavailable or returned invalid data: {last_error}") from last_error

    def _limit_text(self, text: str) -> str:
        if len(text) <= self.text_limit:
            return text
        return text[: self.text_limit]

    @staticmethod
    def _parse_response(data: dict, expected_count: int) -> list[list[float]]:
        rows = data["data"]
        if len(rows) != expected_count:
            raise EmbeddingError(f"expected {expected_count} embeddings, got {len(rows)}")
        if all("index" in row for row in rows):
            rows = sorted(rows, key=lambda row: row["index"])
        vectors = [row["embedding"] for row in rows]
        if not all(isinstance(vector, list) and vector for vector in vectors):
            raise EmbeddingError("embedding response contains empty or invalid vectors")
        return vectors
