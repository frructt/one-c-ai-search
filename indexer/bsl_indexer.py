from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from common.logging import configure_logging
from common.settings import Settings, load_settings
from indexer.bsl_splitter import split_bsl
from indexer.chunk_builder import build_chunk
from indexer.embedder_client import EmbeddingClient, EmbeddingError
from indexer.git_utils import current_commit
from indexer.index_common import IndexFailure, make_embedder, print_failures, record_failure
from indexer.weaviate_writer import WeaviateWriteError, WeaviateWriter


LOGGER = logging.getLogger(__name__)


@dataclass
class BslIndexStats:
    files_scanned: int = 0
    files_failed: int = 0
    chunks_failed: int = 0
    chunks_created: int = 0
    chunks_uploaded: int = 0
    embedding_errors: int = 0
    weaviate_errors: int = 0
    duration_seconds: float = 0.0
    failures: list[IndexFailure] = field(default_factory=list)

    def record_failure(self, *, stage: str, path: str | Path, message: str, symbol_name: str = "") -> None:
        record_failure(
            self.failures,
            stage=stage,
            path=path,
            message=message,
            symbol_name=symbol_name,
        )


def run_bsl_index(settings: Settings) -> BslIndexStats:
    settings.require_repo_path()
    source_commit = current_commit(settings.repo_path)
    embedder = make_embedder(settings)
    writer = WeaviateWriter(settings)
    try:
        writer.ensure_schema()
        return index_bsl(
            settings=settings,
            embedder=embedder,
            writer=writer,
            source_commit=source_commit,
        )
    finally:
        embedder.close()
        writer.close()


def index_bsl(
    *,
    settings: Settings,
    embedder: EmbeddingClient,
    writer: WeaviateWriter,
    source_commit: str,
) -> BslIndexStats:
    started = time.monotonic()
    stats = BslIndexStats()
    repo_path = settings.repo_path
    LOGGER.info("start BSL indexing repo=%s branch=%s path=%s", settings.repo_name, settings.branch, repo_path)
    files = sorted(repo_path.rglob("*.bsl"))
    LOGGER.info("number of BSL files found: %s", len(files))

    pending = []
    for file_path in files:
        stats.files_scanned += 1
        try:
            code = file_path.read_text(encoding="utf-8")
            symbols = split_bsl(code)
        except Exception as exc:
            stats.files_failed += 1
            stats.record_failure(stage="read_or_parse", path=file_path, message=str(exc))
            LOGGER.warning("failed to parse file %s: %s", file_path, exc)
            continue

        for symbol in symbols:
            try:
                chunk = build_chunk(
                    repo=settings.repo_name,
                    branch=settings.branch,
                    path=file_path,
                    repo_path=repo_path,
                    symbol=symbol,
                    settings=settings,
                    source_commit=source_commit,
                )
                pending.append(chunk)
                stats.chunks_created += 1
            except Exception as exc:
                stats.chunks_failed += 1
                stats.record_failure(
                    stage="build_chunk",
                    path=file_path,
                    message=str(exc),
                    symbol_name=symbol.symbol_name,
                )
                LOGGER.warning("failed to build chunk for %s: %s", file_path, exc)

            if len(pending) >= settings.embedding_batch_size:
                _flush(pending, embedder, writer, stats)
                pending.clear()

    if pending:
        _flush(pending, embedder, writer, stats)
        pending.clear()

    stats.duration_seconds = round(time.monotonic() - started, 2)
    LOGGER.info("BSL chunks created: %s", stats.chunks_created)
    LOGGER.info("BSL chunks uploaded: %s", stats.chunks_uploaded)
    return stats


def _flush(
    pending,
    embedder: EmbeddingClient,
    writer: WeaviateWriter,
    stats: BslIndexStats,
) -> None:
    try:
        vectors = embedder.embed_batch([chunk.search_text for chunk in pending])
    except EmbeddingError as exc:
        stats.embedding_errors += len(pending)
        for chunk in pending:
            stats.record_failure(
                stage="embedding",
                path=chunk.path,
                message=str(exc),
                symbol_name=chunk.symbol_name,
            )
        LOGGER.warning("failed to embed chunk batch size=%s: %s", len(pending), exc)
        return

    try:
        uploaded = writer.write_chunks(pending, vectors)
        stats.chunks_uploaded += uploaded
    except WeaviateWriteError as exc:
        stats.weaviate_errors += len(pending)
        for chunk in pending:
            stats.record_failure(
                stage="weaviate_write",
                path=chunk.path,
                message=str(exc),
                symbol_name=chunk.symbol_name,
            )
        LOGGER.warning("failed to upload chunk batch size=%s: %s", len(pending), exc)


def print_stats(stats: BslIndexStats) -> None:
    print("BSL indexing statistics:")
    for name in (
        "files_scanned",
        "files_failed",
        "chunks_failed",
        "chunks_created",
        "chunks_uploaded",
        "embedding_errors",
        "weaviate_errors",
        "duration_seconds",
    ):
        print(f"{name}: {getattr(stats, name)}")
    print_failures(stats.failures)


def bsl_index_exit_code(stats: BslIndexStats, settings: Settings) -> int:
    if stats.embedding_errors or stats.weaviate_errors:
        return 2
    if settings.indexer_fail_on_failed_files and (stats.files_failed or stats.chunks_failed):
        return 2
    return 0


def main() -> int:
    configure_logging()
    settings = load_settings()
    try:
        stats = run_bsl_index(settings)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return 1
    except Exception as exc:
        LOGGER.error("BSL indexing failed: %s", exc)
        return 1

    print_stats(stats)
    return bsl_index_exit_code(stats, settings)


if __name__ == "__main__":
    raise SystemExit(main())
