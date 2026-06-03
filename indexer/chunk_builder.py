from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from common.models import CodeChunk, SymbolChunk
from common.settings import Settings


IDENTIFIER_RE = re.compile(r"[А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*")
STOP_WORDS = {
    "Процедура",
    "КонецПроцедуры",
    "Функция",
    "КонецФункции",
    "Если",
    "Тогда",
    "Иначе",
    "КонецЕсли",
    "Для",
    "Каждого",
    "Из",
    "Цикл",
    "КонецЦикла",
    "Пока",
    "Возврат",
    "Попытка",
    "Исключение",
    "КонецПопытки",
    "Экспорт",
    "Истина",
    "Ложь",
    "Неопределено",
    "NULL",
}

OBJECT_TYPE_BY_FOLDER = {
    "AccumulationRegisters": "AccumulationRegister",
    "BusinessProcesses": "BusinessProcess",
    "Catalogs": "Catalog",
    "ChartsOfAccounts": "ChartOfAccounts",
    "ChartsOfCharacteristicTypes": "ChartOfCharacteristicTypes",
    "CommonCommands": "CommonCommand",
    "CommonModules": "CommonModule",
    "Constants": "Constant",
    "Documents": "Document",
    "Enums": "Enum",
    "ExchangePlans": "ExchangePlan",
    "InformationRegisters": "InformationRegister",
    "Reports": "Report",
    "Tasks": "Task",
}


def build_chunk(
    *,
    repo: str,
    branch: str,
    path: str | Path,
    repo_path: Path,
    symbol: SymbolChunk,
    settings: Settings,
    source_commit: str,
    indexed_at: str | None = None,
) -> CodeChunk:
    relative_path = normalize_repo_path(path, repo_path)
    module_name, object_name, object_type = parse_1c_path(relative_path)
    identifiers = extract_identifiers(symbol.code)
    chunk_id = stable_chunk_id(repo, branch, relative_path, symbol.symbol_name, symbol.start_line)
    content_hash = sha256_text(symbol.code)
    gitlab_url = build_gitlab_url(settings, branch, relative_path, symbol.start_line)
    indexed_at = indexed_at or datetime.now(timezone.utc).isoformat()
    search_text = build_search_text(
        repo=repo,
        branch=branch,
        path=relative_path,
        object_type=object_type,
        module_name=module_name,
        symbol_name=symbol.symbol_name,
        symbol_type=symbol.symbol_type,
        identifiers=identifiers,
        code=symbol.code,
        text_limit=settings.embedding_text_limit,
    )
    return CodeChunk(
        repo=repo,
        branch=branch,
        path=relative_path,
        gitlab_url=gitlab_url,
        module_name=module_name,
        object_name=object_name,
        object_type=object_type,
        symbol_name=symbol.symbol_name,
        symbol_type=symbol.symbol_type,
        start_line=symbol.start_line,
        end_line=symbol.end_line,
        code=symbol.code,
        identifiers=identifiers,
        search_text=search_text,
        chunk_id=chunk_id,
        source_commit=source_commit,
        indexed_at=indexed_at,
        content_hash=content_hash,
    )


def normalize_repo_path(path: str | Path, repo_path: Path) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            candidate = candidate.relative_to(repo_path)
        except ValueError:
            pass
    return candidate.as_posix()


def parse_1c_path(path: str) -> tuple[str, str, str]:
    parts = list(PurePosixPath(path).parts)
    if "configuration" in parts:
        parts = parts[parts.index("configuration") + 1 :]
    elif "src" in parts:
        parts = parts[parts.index("src") + 1 :]

    if len(parts) >= 2:
        folder = parts[0]
        object_name = parts[1]
        object_type = OBJECT_TYPE_BY_FOLDER.get(folder, "Unknown")
        if "Forms" in parts:
            form_index = parts.index("Forms")
            if len(parts) > form_index + 1:
                form_name = parts[form_index + 1]
                return f"{object_name}.{form_name}", object_name, "Form"
        return object_name, object_name, object_type

    pure = PurePosixPath(path)
    fallback = pure.parent.name or pure.stem or path
    return fallback, fallback, "Unknown"


def extract_identifiers(code: str, limit: int = 200) -> list[str]:
    seen_lower: set[str] = set()
    identifiers: list[str] = []
    for match in IDENTIFIER_RE.finditer(code):
        word = match.group(0)
        if len(word) < 3 or word in STOP_WORDS:
            continue
        key = word.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        identifiers.append(word)
        if len(identifiers) >= limit:
            break
    return identifiers


def build_search_text(
    *,
    repo: str,
    branch: str,
    path: str,
    object_type: str,
    module_name: str,
    symbol_name: str,
    symbol_type: str,
    identifiers: list[str],
    code: str,
    text_limit: int,
) -> str:
    prefix = "\n".join(
        [
            f"Репозиторий: {repo}",
            f"Ветка: {branch}",
            f"Путь: {path}",
            f"Тип объекта: {object_type}",
            f"Модуль: {module_name}",
            f"Символ: {symbol_name}",
            f"Тип символа: {symbol_type}",
            f"Идентификаторы: {', '.join(identifiers)}",
            "Код:",
        ]
    )
    remaining = max(0, text_limit - len(prefix) - 20)
    code_part = code if len(code) <= remaining else code[:remaining] + "\n... [truncated]"
    return f"{prefix}\n{code_part}"


def build_gitlab_url(settings: Settings, branch: str, path: str, start_line: int) -> str:
    quoted_branch = quote(branch, safe="")
    quoted_path = quote(path, safe="/")
    return (
        f"{settings.gitlab_base_url}/{settings.gitlab_project_path}"
        f"/-/blob/{quoted_branch}/{quoted_path}#L{start_line}"
    )


def stable_chunk_id(repo: str, branch: str, path: str, symbol_name: str, start_line: int) -> str:
    return sha256_text(f"{repo}|{branch}|{path}|{symbol_name}|{start_line}")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
