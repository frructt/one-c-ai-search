from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from indexer.chunk_builder import OBJECT_TYPE_BY_FOLDER, normalize_repo_path


@dataclass(frozen=True)
class ScannedXml:
    path: Path
    relative_path: str
    known: bool
    object_folder: str = ""
    object_name: str = ""
    object_type: str = ""
    object_dir: str = ""


@dataclass
class MetadataScanResult:
    known_xml: list[ScannedXml] = field(default_factory=list)
    unknown_xml: list[ScannedXml] = field(default_factory=list)


def scan_metadata_xml(repo_path: Path) -> MetadataScanResult:
    result = MetadataScanResult()
    for path in sorted(repo_path.rglob("*.xml")):
        scanned = classify_xml_path(path, repo_path)
        if scanned.known:
            result.known_xml.append(scanned)
        else:
            result.unknown_xml.append(scanned)
    return result


def classify_xml_path(path: Path, repo_path: Path) -> ScannedXml:
    relative_path = normalize_repo_path(path, repo_path)
    parts = list(PurePosixPath(relative_path).parts)
    if not parts:
        return ScannedXml(path=path, relative_path=relative_path, known=False)

    start_index = _object_scope_start(parts)
    scoped = parts[start_index:]
    if len(scoped) < 2:
        return ScannedXml(path=path, relative_path=relative_path, known=False)

    object_folder = scoped[0]
    object_type = OBJECT_TYPE_BY_FOLDER.get(object_folder, "")
    if not object_type:
        return ScannedXml(path=path, relative_path=relative_path, known=False)

    object_name = scoped[1]
    object_dir = PurePosixPath(*parts[: start_index + 2]).as_posix()
    return ScannedXml(
        path=path,
        relative_path=relative_path,
        known=True,
        object_folder=object_folder,
        object_name=object_name,
        object_type=object_type,
        object_dir=object_dir,
    )


def group_by_metadata_object(scanned_xml: list[ScannedXml]) -> dict[str, list[ScannedXml]]:
    grouped: dict[str, list[ScannedXml]] = {}
    for scanned in scanned_xml:
        grouped.setdefault(scanned.object_dir, []).append(scanned)
    return grouped


def _object_scope_start(parts: list[str]) -> int:
    if "configuration" in parts:
        return parts.index("configuration") + 1
    if "src" in parts:
        return parts.index("src") + 1
    return 0
