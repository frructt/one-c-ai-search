from __future__ import annotations

import re
from collections.abc import Iterable

from api.search_models import SearchCandidate


TOKEN_RE = re.compile(r"[А-Яа-яA-Za-z0-9_]{3,}")
ARCHIVE_MARKERS = ("archive", "old", "backup", "deprecated", "архив")


def query_tokens(query: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for match in TOKEN_RE.finditer(query.lower()):
        token = match.group(0)
        if token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def rerank(items: list[dict], query: str) -> list[dict]:
    tokens = query_tokens(query)
    has_concrete = any(item.get("symbol_type") in {"procedure", "function"} for item in items)
    reranked = []
    for item in items:
        final_score = _candidate_score(item, tokens=tokens, has_concrete=has_concrete)
        updated = dict(item)
        updated["final_score"] = round(final_score, 6)
        reranked.append(updated)
    return sorted(reranked, key=lambda item: item["final_score"], reverse=True)


def rerank_candidates(items: list[SearchCandidate], query: str) -> list[SearchCandidate]:
    tokens = query_tokens(query)
    has_concrete = any(item.symbol_type in {"procedure", "function"} for item in items)
    reranked = [
        item.with_score(final_score=_candidate_score(item, tokens=tokens, has_concrete=has_concrete))
        for item in items
    ]
    return sorted(reranked, key=lambda item: item.final_score, reverse=True)


def rank_files(items: list[SearchCandidate], query: str) -> list[SearchCandidate]:
    reranked = rerank_candidates(items, query)
    by_path: dict[str, list[SearchCandidate]] = {}
    for item in reranked:
        by_path.setdefault(item.path, []).append(item)

    file_candidates: list[SearchCandidate] = []
    for path, path_items in by_path.items():
        sorted_items = sorted(path_items, key=lambda item: item.final_score, reverse=True)
        best = sorted_items[0]
        top_scores = [item.final_score for item in sorted_items[:3]]
        secondary_score = sum(top_scores[1:]) * 0.15
        matched_profiles = {
            profile
            for item in sorted_items
            for profile in item.retrieval_profiles
        }
        profile_bonus = min(0.16, 0.04 * max(0, len(matched_profiles) - 1))
        chunk_bonus = min(0.10, 0.02 * max(0, len(sorted_items) - 1))
        file_score = best.final_score + secondary_score + profile_bonus + chunk_bonus
        if any(marker in path.lower() for marker in ARCHIVE_MARKERS):
            file_score -= 0.25
        file_candidates.append(best.with_score(final_score=file_score))

    return sorted(
        file_candidates,
        key=lambda item: (item.final_score, item.score, -item.original_rank),
        reverse=True,
    )


def build_why(item: dict | SearchCandidate, query: str) -> list[str]:
    tokens = query_tokens(query)
    reasons: list[str] = []

    for token in tokens:
        if _contains(_get(item, "symbol_name"), token) or _contains(_get(item, "module_name"), token):
            reasons.append(f"найдено совпадение по слову: {token}")
        elif _contains(_get(item, "identifiers"), token):
            reasons.append(f"найден идентификатор по слову: {token}")
        elif _contains(_get(item, "path"), token):
            reasons.append(f"путь содержит слово: {token}")
        if len(reasons) >= 3:
            break

    if _get(item, "symbol_type") in {"procedure", "function"}:
        reasons.append(f"найден конкретный символ: {_get(item, 'symbol_name')}")
    if _get(item, "module_name"):
        reasons.append(f"модуль: {_get(item, 'module_name')}")
    profiles = _get(item, "retrieval_profiles")
    if profiles:
        reasons.append(f"поисковые профили: {', '.join(str(profile) for profile in profiles)}")
    if not reasons:
        reasons.append("гибридный поиск поднял этот фрагмент в результаты")
    return reasons[:5]


def _candidate_score(item: dict | SearchCandidate, *, tokens: list[str], has_concrete: bool) -> float:
    final_score = float(_get(item, "score") or 0.0)
    final_score += _match_bonus(tokens, _get(item, "symbol_name"), 0.08)
    final_score += _match_bonus(tokens, _get(item, "module_name"), 0.05)
    final_score += _match_bonus(tokens, _get(item, "identifiers"), 0.04)
    final_score += _match_bonus(tokens, _get(item, "path"), 0.03)
    path = str(_get(item, "path") or "").lower()
    if any(marker in path for marker in ARCHIVE_MARKERS):
        final_score -= 0.25
    if has_concrete and _get(item, "symbol_type") == "module":
        final_score -= 0.10
    return final_score


def _match_bonus(tokens: list[str], value, weight: float) -> float:
    return weight if any(_contains(value, token) for token in tokens) else 0.0


def _contains(value, token: str) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return token in value.lower()
    if isinstance(value, Iterable):
        return any(token in str(item).lower() for item in value)
    return token in str(value).lower()


def _get(item: dict | SearchCandidate, name: str):
    if isinstance(item, SearchCandidate):
        return getattr(item, name)
    return item.get(name)
