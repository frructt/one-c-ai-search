from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from common.logging import configure_logging
from common.settings import Settings, load_settings
from indexer.embedder_client import EmbeddingClient, EmbeddingError
from indexer.git_utils import current_commit
from indexer.index_common import IndexFailure, make_embedder, print_failures, record_failure
from indexer.metadata_builder import build_metadata_object
from indexer.metadata_parser import MetadataParseError, parse_metadata_xml
from indexer.metadata_scanner import ScannedXml, group_by_metadata_object, scan_metadata_xml
from indexer.weaviate_writer import WeaviateWriteError, WeaviateWriter


LOGGER = logging.getLogger(__name__)


@dataclass
class MetadataIndexStats:
    files_scanned: int = 0
    known_xml: int = 0
    unknown_xml: int = 0
    files_failed: int = 0
    objects_failed: int = 0
    objects_created: int = 0
    objects_uploaded: int = 0
    embedding_errors: int = 0
    weaviate_errors: int = 0
    duration_seconds: float = 0.0
    failures: list[IndexFailure] = field(default_factory=list)
    unknown_xml_paths: list[str] = field(default_factory=list)

    def record_failure(self, *, stage: str, path: str | Path, message: str, symbol_name: str = "") -> None:
        record_failure(
            self.failures,
            stage=stage,
            path=path,
            message=message,
            symbol_name=symbol_name,
        )


def run_metadata_index(settings: Settings) -> MetadataIndexStats:
    settings.require_repo_path()
    source_commit = current_commit(settings.repo_path)
    embedder = make_embedder(settings)
    writer = WeaviateWriter(settings)
    try:
        writer.ensure_metadata_schema()
        return index_metadata(
            settings=settings,
            embedder=embedder,
            writer=writer,
            source_commit=source_commit,
        )
    finally:
        embedder.close()
        writer.close()


def index_metadata(
    *,
    settings: Settings,
    embedder: EmbeddingClient,
    writer: WeaviateWriter,
    source_commit: str,
) -> MetadataIndexStats:
    started = time.monotonic()
    stats = MetadataIndexStats()
    repo_path = settings.repo_path
    LOGGER.info("start metadata indexing repo=%s branch=%s path=%s", settings.repo_name, settings.branch, repo_path)

    scan_result = scan_metadata_xml(repo_path)
    stats.known_xml = len(scan_result.known_xml)
    stats.unknown_xml = len(scan_result.unknown_xml)
    stats.files_scanned = stats.known_xml + stats.unknown_xml
    stats.unknown_xml_paths = [scanned.relative_path for scanned in scan_result.unknown_xml]
    LOGGER.info(
        "metadata XML scan complete known=%s unknown=%s",
        stats.known_xml,
        stats.unknown_xml,
    )

    pending = []
    for scanned_group in group_by_metadata_object(scan_result.known_xml).values():
        parsed_files = []
        for scanned in scanned_group:
            try:
                parsed_files.append(parse_metadata_xml(scanned.path))
            except MetadataParseError as exc:
                stats.files_failed += 1
                stats.record_failure(stage="parse_metadata_xml", path=scanned.path, message=str(exc))
                LOGGER.warning("failed to parse metadata XML %s: %s", scanned.path, exc)

        try:
            metadata_object = build_metadata_object(
                repo=settings.repo_name,
                branch=settings.branch,
                repo_path=repo_path,
                scanned_xml=scanned_group,
                parsed_files=parsed_files,
                settings=settings,
                source_commit=source_commit,
            )
            pending.append(metadata_object)
            stats.objects_created += 1
        except Exception as exc:
            stats.objects_failed += 1
            first_path = _first_path(scanned_group)
            stats.record_failure(stage="build_metadata_object", path=first_path, message=str(exc))
            LOGGER.warning("failed to build metadata object for %s: %s", first_path, exc)

        if len(pending) >= settings.embedding_batch_size:
            _flush_metadata(pending, embedder, writer, stats)
            pending.clear()

    if pending:
        _flush_metadata(pending, embedder, writer, stats)
        pending.clear()

    stats.duration_seconds = round(time.monotonic() - started, 2)
    LOGGER.info("metadata objects created: %s", stats.objects_created)
    LOGGER.info("metadata objects uploaded: %s", stats.objects_uploaded)
    return stats


def _flush_metadata(
    pending,
    embedder: EmbeddingClient,
    writer: WeaviateWriter,
    stats: MetadataIndexStats,
) -> None:
    try:
        vectors = embedder.embed_batch([item.search_text for item in pending])
    except EmbeddingError as exc:
        stats.embedding_errors += len(pending)
        for item in pending:
            stats.record_failure(
                stage="metadata_embedding",
                path=item.path,
                message=str(exc),
                symbol_name=item.object_name,
            )
        LOGGER.warning("failed to embed metadata batch size=%s: %s", len(pending), exc)
        return

    try:
        uploaded = writer.write_metadata_objects(pending, vectors)
        stats.objects_uploaded += uploaded
    except WeaviateWriteError as exc:
        stats.weaviate_errors += len(pending)
        for item in pending:
            stats.record_failure(
                stage="metadata_weaviate_write",
                path=item.path,
                message=str(exc),
                symbol_name=item.object_name,
            )
        LOGGER.warning("failed to upload metadata batch size=%s: %s", len(pending), exc)


def print_metadata_stats(stats: MetadataIndexStats) -> None:
    print("Metadata indexing statistics:")
    for name in (
        "files_scanned",
        "known_xml",
        "unknown_xml",
        "files_failed",
        "objects_failed",
        "objects_created",
        "objects_uploaded",
        "embedding_errors",
        "weaviate_errors",
        "duration_seconds",
    ):
        print(f"{name}: {getattr(stats, name)}")
    if stats.unknown_xml_paths:
        print()
        print("Unknown XML files:")
        for path in stats.unknown_xml_paths:
            print(f"- {path}")
    print_failures(stats.failures)


def metadata_index_exit_code(stats: MetadataIndexStats, settings: Settings) -> int:
    if stats.embedding_errors or stats.weaviate_errors:
        return 2
    if settings.indexer_fail_on_failed_files and (stats.files_failed or stats.objects_failed):
        return 2
    return 0


def main() -> int:
    configure_logging()
    settings = load_settings()
    try:
        stats = run_metadata_index(settings)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return 1
    except Exception as exc:
        LOGGER.error("metadata indexing failed: %s", exc)
        return 1

    print_metadata_stats(stats)
    return metadata_index_exit_code(stats, settings)


def _first_path(scanned_group: list[ScannedXml]) -> str:
    if not scanned_group:
        return ""
    return scanned_group[0].relative_path


if __name__ == "__main__":
    raise SystemExit(main())
