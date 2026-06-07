from __future__ import annotations

import logging
import time
from typing import Any

from openai import OpenAI, OpenAIError

from api.query_expansion import expand_query
from common.openai_response import response_field


LOGGER = logging.getLogger(__name__)


class LlmError(RuntimeError):
    pass


class LlmClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 10,
        retries: int = 1,
        max_tokens: int = 512,
        client: Any | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.max_tokens = max_tokens
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

    def expand_query(self, query: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "Ты расширяешь поисковые запросы для поиска мест изменения в 1С BSL коде. "
                    "Верни только один расширенный поисковый запрос без пояснений. "
                    "Сохрани исходный смысл, добавь релевантные синонимы, термины предметной области, "
                    "имена типичных 1С сущностей и методов, если они помогают поиску."
                ),
            },
            {"role": "user", "content": query},
        ]
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0,
                    max_tokens=self.max_tokens,
                )
                return self._parse_response(response, original_query=query)
            except (OpenAIError, LlmError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
                status_code = getattr(exc, "status_code", None)
                if status_code is not None and status_code < 500:
                    break
                if attempt < self.retries:
                    time.sleep(min(2 ** (attempt - 1), 4))
        raise LlmError(f"LLM endpoint unavailable or returned invalid data: {last_error}") from last_error

    @staticmethod
    def _parse_response(data: Any, *, original_query: str) -> str:
        choices = response_field(data, "choices")
        if not choices:
            raise LlmError("LLM response does not contain choices")
        message = response_field(choices[0], "message")
        content = response_field(message, "content")
        if isinstance(content, list):
            content = "\n".join(str(part) for part in content)
        if not isinstance(content, str):
            raise LlmError("LLM response content is not text")
        expanded = _clean_response_text(content)
        if not expanded:
            raise LlmError("LLM response content is empty")
        if original_query.lower() not in expanded.lower():
            return f"{original_query}\nДополнение LLM: {expanded}"
        return expanded


def expand_query_for_search(query: str, llm_client: LlmClient | None) -> str:
    fallback_query = expand_query(query)
    if llm_client is None:
        return fallback_query
    try:
        return llm_client.expand_query(query)
    except LlmError as exc:
        LOGGER.warning("LLM query expansion failed, using dictionary fallback: %s", exc)
        return fallback_query


def _clean_response_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = [line for line in cleaned.splitlines() if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    for prefix in ("Расширенный запрос:", "Запрос:", "Expanded query:"):
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix) :].strip()
    return cleaned.strip().strip('"')
