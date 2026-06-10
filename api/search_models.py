from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from common.models import SymbolType


@dataclass(frozen=True)
class RetrievalProfile:
    name: str
    alpha: float
    query_properties: tuple[str, ...]
    limit_scale: float = 1.0

    def limit_for(self, internal_limit: int) -> int:
        return max(1, int(round(internal_limit * self.limit_scale)))


@dataclass(frozen=True)
class SearchCandidate:
    repo: str
    branch: str
    path: str
    gitlab_url: str
    module_name: str
    object_name: str
    object_type: str
    symbol_name: str
    symbol_type: SymbolType
    start_line: int
    end_line: int
    code: str
    identifiers: list[str]
    search_text: str
    chunk_id: str
    source_commit: str
    indexed_at: str
    content_hash: str
    score: float
    final_score: float
    retrieval_profiles: tuple[str, ...]
    original_rank: int
    metadata_boost: float = 0.0
    metadata_evidence: tuple[str, ...] = ()

    @classmethod
    def from_properties(
        cls,
        properties: dict[str, Any],
        *,
        score: float,
        retrieval_profile: str,
        original_rank: int,
    ) -> "SearchCandidate":
        symbol_type = _symbol_type(properties.get("symbol_type"))
        return cls(
            repo=_string(properties.get("repo")),
            branch=_string(properties.get("branch")),
            path=_string(properties.get("path")),
            gitlab_url=_string(properties.get("gitlab_url")),
            module_name=_string(properties.get("module_name")),
            object_name=_string(properties.get("object_name")),
            object_type=_string(properties.get("object_type")),
            symbol_name=_string(properties.get("symbol_name")),
            symbol_type=symbol_type,
            start_line=_int(properties.get("start_line")),
            end_line=_int(properties.get("end_line")),
            code=_string(properties.get("code")),
            identifiers=_strings(properties.get("identifiers")),
            search_text=_string(properties.get("search_text")),
            chunk_id=_string(properties.get("chunk_id")),
            source_commit=_string(properties.get("source_commit")),
            indexed_at=_string(properties.get("indexed_at")),
            content_hash=_string(properties.get("content_hash")),
            score=score,
            final_score=score,
            retrieval_profiles=(retrieval_profile,),
            original_rank=original_rank,
        )

    def with_score(self, *, score: float | None = None, final_score: float | None = None) -> "SearchCandidate":
        return replace(
            self,
            score=self.score if score is None else round(score, 6),
            final_score=self.final_score if final_score is None else round(final_score, 6),
        )

    def with_metadata(
        self,
        *,
        metadata_boost: float,
        metadata_evidence: tuple[str, ...],
    ) -> "SearchCandidate":
        return replace(
            self,
            metadata_boost=round(metadata_boost, 6),
            metadata_evidence=metadata_evidence,
        )

    def merge(self, other: "SearchCandidate") -> "SearchCandidate":
        profiles = tuple(dict.fromkeys((*self.retrieval_profiles, *other.retrieval_profiles)))
        evidence = tuple(dict.fromkeys((*self.metadata_evidence, *other.metadata_evidence)))
        return replace(
            self if self.score >= other.score else other,
            score=max(self.score, other.score),
            final_score=max(self.final_score, other.final_score),
            retrieval_profiles=profiles,
            original_rank=min(self.original_rank, other.original_rank),
            metadata_boost=max(self.metadata_boost, other.metadata_boost),
            metadata_evidence=evidence,
        )

    def key(self) -> str:
        if self.chunk_id:
            return self.chunk_id
        return f"{self.path}|{self.symbol_name}|{self.start_line}"


@dataclass(frozen=True)
class MetadataCandidate:
    repo: str
    branch: str
    path: str
    object_name: str
    object_type: str
    synonym: str
    comment: str
    attributes: list[str]
    tabular_sections: list[str]
    forms: list[str]
    commands: list[str]
    related_bsl_paths: list[str]
    search_text: str
    metadata_id: str
    source_commit: str
    indexed_at: str
    content_hash: str
    score: float
    original_rank: int

    @classmethod
    def from_properties(
        cls,
        properties: dict[str, Any],
        *,
        score: float,
        original_rank: int,
    ) -> "MetadataCandidate":
        return cls(
            repo=_string(properties.get("repo")),
            branch=_string(properties.get("branch")),
            path=_string(properties.get("path")),
            object_name=_string(properties.get("object_name")),
            object_type=_string(properties.get("object_type")),
            synonym=_string(properties.get("synonym")),
            comment=_string(properties.get("comment")),
            attributes=_strings(properties.get("attributes")),
            tabular_sections=_strings(properties.get("tabular_sections")),
            forms=_strings(properties.get("forms")),
            commands=_strings(properties.get("commands")),
            related_bsl_paths=_strings(properties.get("related_bsl_paths")),
            search_text=_string(properties.get("search_text")),
            metadata_id=_string(properties.get("metadata_id")),
            source_commit=_string(properties.get("source_commit")),
            indexed_at=_string(properties.get("indexed_at")),
            content_hash=_string(properties.get("content_hash")),
            score=score,
            original_rank=original_rank,
        )

    def evidence_text(self) -> str:
        label = f"{self.object_type} {self.object_name}".strip()
        if self.synonym:
            label = f"{label} ({self.synonym})" if label else self.synonym
        return f"метаданные: {label}" if label else "метаданные объекта"


def default_retrieval_profiles(search_alpha: float) -> tuple[RetrievalProfile, ...]:
    base_properties = (
        "search_text^3",
        "symbol_name^2",
        "module_name^2",
        "identifiers",
        "path",
    )
    metadata_properties = (
        "symbol_name^4",
        "module_name^4",
        "identifiers^2",
        "path^2",
        "search_text",
    )
    return (
        RetrievalProfile(
            name="balanced",
            alpha=search_alpha,
            query_properties=base_properties,
            limit_scale=1.0,
        ),
        RetrievalProfile(
            name="keyword",
            alpha=0.05,
            query_properties=metadata_properties,
            limit_scale=0.75,
        ),
        RetrievalProfile(
            name="vector",
            alpha=0.85,
            query_properties=("search_text",),
            limit_scale=0.75,
        ),
        RetrievalProfile(
            name="metadata",
            alpha=0.2,
            query_properties=metadata_properties,
            limit_scale=0.75,
        ),
    )


def dedupe_candidates(candidates: list[SearchCandidate]) -> list[SearchCandidate]:
    by_key: dict[str, SearchCandidate] = {}
    for candidate in candidates:
        key = candidate.key()
        existing = by_key.get(key)
        by_key[key] = candidate if existing is None else existing.merge(candidate)
    return list(by_key.values())


def _string(value: Any) -> str:
    return "" if value is None else str(value)


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return [str(value)]


def _symbol_type(value: Any) -> SymbolType:
    if value in {"procedure", "function", "module"}:
        return value
    return "module"
