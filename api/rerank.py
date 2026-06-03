from __future__ import annotations

import re
from collections.abc import Iterable


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
        final_score = float(item.get("score") or 0.0)
        final_score += _match_bonus(tokens, item.get("symbol_name"), 0.08)
        final_score += _match_bonus(tokens, item.get("module_name"), 0.05)
        final_score += _match_bonus(tokens, item.get("identifiers"), 0.04)
        final_score += _match_bonus(tokens, item.get("path"), 0.03)
        path = str(item.get("path") or "").lower()
        if any(marker in path for marker in ARCHIVE_MARKERS):
            final_score -= 0.25
        if has_concrete and item.get("symbol_type") == "module":
            final_score -= 0.10
        updated = dict(item)
        updated["final_score"] = round(final_score, 6)
        reranked.append(updated)
    return sorted(reranked, key=lambda item: item["final_score"], reverse=True)


def build_why(item: dict, query: str) -> list[str]:
    tokens = query_tokens(query)
    reasons: list[str] = []

    for token in tokens:
        if _contains(item.get("symbol_name"), token) or _contains(item.get("module_name"), token):
            reasons.append(f"найдено совпадение по слову: {token}")
        elif _contains(item.get("identifiers"), token):
            reasons.append(f"найден идентификатор по слову: {token}")
        elif _contains(item.get("path"), token):
            reasons.append(f"путь содержит слово: {token}")
        if len(reasons) >= 3:
            break

    if item.get("symbol_type") in {"procedure", "function"}:
        reasons.append(f"найден конкретный символ: {item.get('symbol_name')}")
    if item.get("module_name"):
        reasons.append(f"модуль: {item.get('module_name')}")
    if not reasons:
        reasons.append("гибридный поиск поднял этот фрагмент в результаты")
    return reasons[:5]


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
