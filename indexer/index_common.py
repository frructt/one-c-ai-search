from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from common.settings import Settings
from indexer.embedder_client import EmbeddingClient


@dataclass
class IndexFailure:
    stage: str
    path: str
    message: str
    symbol_name: str = ""


def make_embedder(settings: Settings) -> EmbeddingClient:
    return EmbeddingClient(
        base_url=settings.embeddings_base_url,
        api_key=settings.embeddings_api_key,
        model=settings.embeddings_model,
        timeout_seconds=settings.embedding_timeout_seconds,
        retries=settings.embedding_retries,
        text_limit=settings.embedding_text_limit,
    )


def record_failure(
    failures: list[IndexFailure],
    *,
    stage: str,
    path: str | Path,
    message: str,
    symbol_name: str = "",
) -> None:
    failures.append(
        IndexFailure(
            stage=stage,
            path=str(path),
            message=message,
            symbol_name=symbol_name,
        )
    )


def print_failures(failures: list[IndexFailure]) -> None:
    if not failures:
        return
    print()
    print("Indexing failures:")
    for failure in failures:
        symbol = f" symbol={failure.symbol_name}" if failure.symbol_name else ""
        print(f"- stage={failure.stage} path={failure.path}{symbol} message={failure.message}")
