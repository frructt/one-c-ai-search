from __future__ import annotations

import re

from common.models import SymbolChunk


START_RE = re.compile(
    r"^\s*(Процедура|Функция)\s+([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)\s*\(",
    re.IGNORECASE,
)
END_RE = {
    "procedure": re.compile(r"^\s*КонецПроцедуры\b", re.IGNORECASE),
    "function": re.compile(r"^\s*КонецФункции\b", re.IGNORECASE),
}


def split_bsl(code: str) -> list[SymbolChunk]:
    lines = code.splitlines(keepends=True)
    if not lines:
        return [_module_chunk(code, 1, 0)]

    chunks: list[SymbolChunk] = []
    active_type: str | None = None
    active_name: str | None = None
    active_start = 0

    for index, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue

        if active_type is None:
            match = START_RE.match(line)
            if not match:
                continue
            active_type = "procedure" if match.group(1).lower() == "процедура" else "function"
            active_name = match.group(2)
            active_start = index
            continue

        if END_RE[active_type].match(line):
            chunk_code = "".join(lines[active_start - 1 : index])
            chunks.append(
                SymbolChunk(
                    symbol_name=active_name or "",
                    symbol_type=active_type,  # type: ignore[arg-type]
                    start_line=active_start,
                    end_line=index,
                    code=chunk_code,
                )
            )
            active_type = None
            active_name = None
            active_start = 0

    if active_type is not None:
        return [_module_chunk(code, 1, len(lines))]
    if not chunks:
        return [_module_chunk(code, 1, len(lines))]
    return chunks


def _module_chunk(code: str, start_line: int, end_line: int) -> SymbolChunk:
    return SymbolChunk(
        symbol_name="<module>",
        symbol_type="module",
        start_line=start_line,
        end_line=end_line,
        code=code,
    )
