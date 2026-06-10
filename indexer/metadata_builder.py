from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from common.models import MetadataObject
from common.settings import Settings
from indexer.chunk_builder import normalize_repo_path, sha256_text
from indexer.metadata_parser import ParsedMetadataFile
from indexer.metadata_scanner import ScannedXml


def build_metadata_object(
    *,
    repo: str,
    branch: str,
    repo_path: Path,
    scanned_xml: list[ScannedXml],
    parsed_files: list[ParsedMetadataFile],
    settings: Settings,
    source_commit: str,
    indexed_at: str | None = None,
) -> MetadataObject:
    if not scanned_xml:
        raise ValueError("scanned_xml must not be empty")
    first = scanned_xml[0]
    related_bsl_paths = find_related_bsl_paths(repo_path=repo_path, object_dir=first.object_dir)
    synonym = first_non_empty(parsed.synonym for parsed in parsed_files)
    comment = first_non_empty(parsed.comment for parsed in parsed_files)
    attributes = unique_items(item for parsed in parsed_files for item in parsed.attributes)
    tabular_sections = unique_items(item for parsed in parsed_files for item in parsed.tabular_sections)
    forms = unique_items(item for parsed in parsed_files for item in parsed.forms)
    commands = unique_items(item for parsed in parsed_files for item in parsed.commands)
    indexed_at = indexed_at or datetime.now(timezone.utc).isoformat()
    search_text = build_metadata_search_text(
        repo=repo,
        branch=branch,
        path=first.object_dir,
        object_name=first.object_name,
        object_type=first.object_type,
        synonym=synonym,
        comment=comment,
        attributes=attributes,
        tabular_sections=tabular_sections,
        forms=forms,
        commands=commands,
        related_bsl_paths=related_bsl_paths,
        text_limit=settings.embedding_text_limit,
    )
    metadata_id = stable_metadata_id(repo, branch, first.object_type, first.object_name, first.object_dir)
    content_hash = sha256_text(
        "\n".join(
            [
                first.object_dir,
                search_text,
                *sorted(scanned.relative_path for scanned in scanned_xml),
            ]
        )
    )
    return MetadataObject(
        repo=repo,
        branch=branch,
        path=first.object_dir,
        object_name=first.object_name,
        object_type=first.object_type,
        synonym=synonym,
        comment=comment,
        attributes=attributes,
        tabular_sections=tabular_sections,
        forms=forms,
        commands=commands,
        related_bsl_paths=related_bsl_paths,
        search_text=search_text,
        metadata_id=metadata_id,
        source_commit=source_commit,
        indexed_at=indexed_at,
        content_hash=content_hash,
    )


def find_related_bsl_paths(*, repo_path: Path, object_dir: str) -> list[str]:
    object_path = repo_path / object_dir
    if not object_path.exists():
        return []
    return [
        normalize_repo_path(path, repo_path)
        for path in sorted(object_path.rglob("*.bsl"))
    ]


def build_metadata_search_text(
    *,
    repo: str,
    branch: str,
    path: str,
    object_name: str,
    object_type: str,
    synonym: str,
    comment: str,
    attributes: list[str],
    tabular_sections: list[str],
    forms: list[str],
    commands: list[str],
    related_bsl_paths: list[str],
    text_limit: int,
) -> str:
    text = "\n".join(
        [
            f"Репозиторий: {repo}",
            f"Ветка: {branch}",
            f"Путь: {path}",
            f"Тип объекта: {object_type}",
            f"Объект: {object_name}",
            f"Синоним: {synonym}",
            f"Комментарий: {comment}",
            f"Реквизиты: {', '.join(attributes)}",
            f"Табличные части: {', '.join(tabular_sections)}",
            f"Формы: {', '.join(forms)}",
            f"Команды: {', '.join(commands)}",
            f"Связанные BSL: {', '.join(related_bsl_paths)}",
        ]
    )
    if len(text) <= text_limit:
        return text
    return text[:text_limit].rstrip() + "\n... [truncated]"


def stable_metadata_id(repo: str, branch: str, object_type: str, object_name: str, path: str) -> str:
    return sha256_text(f"{repo}|{branch}|{object_type}|{object_name}|{path}")


def unique_items(values) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = str(value).strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(value)
    return items


def first_non_empty(values) -> str:
    for value in values:
        value = str(value).strip()
        if value:
            return value
    return ""
