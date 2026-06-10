from __future__ import annotations

import logging

from common.logging import configure_logging
from common.settings import load_settings
from indexer.bsl_indexer import (
    BslIndexStats,
    bsl_index_exit_code,
    index_bsl,
    print_stats,
    run_bsl_index,
    _flush,
)
from indexer.git_utils import current_commit
from indexer.index_common import IndexFailure, make_embedder
from indexer.metadata_indexer import (
    index_metadata,
    metadata_index_exit_code,
    print_metadata_stats,
)
from indexer.weaviate_writer import WeaviateWriter


LOGGER = logging.getLogger(__name__)

# Backward-compatible names used by existing tests and local imports.
IndexStats = BslIndexStats


def main() -> int:
    configure_logging()
    settings = load_settings()
    try:
        settings.require_repo_path()
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return 1

    source_commit = current_commit(settings.repo_path)
    embedder = make_embedder(settings)
    writer = WeaviateWriter(settings)
    try:
        try:
            writer.ensure_code_schema()
            writer.ensure_metadata_schema()
        except Exception as exc:
            LOGGER.error("Weaviate unavailable: %s", exc)
            return 1

        bsl_stats = index_bsl(
            settings=settings,
            embedder=embedder,
            writer=writer,
            source_commit=source_commit,
        )
        metadata_stats = index_metadata(
            settings=settings,
            embedder=embedder,
            writer=writer,
            source_commit=source_commit,
        )
    finally:
        embedder.close()
        writer.close()

    print_stats(bsl_stats)
    print()
    print_metadata_stats(metadata_stats)
    return max(
        bsl_index_exit_code(bsl_stats, settings),
        metadata_index_exit_code(metadata_stats, settings),
    )


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BslIndexStats",
    "IndexFailure",
    "IndexStats",
    "_flush",
    "index_bsl",
    "index_metadata",
    "main",
    "print_stats",
    "run_bsl_index",
]
