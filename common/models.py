from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


SymbolType = Literal["procedure", "function", "module"]


@dataclass(frozen=True)
class SymbolChunk:
    symbol_name: str
    symbol_type: SymbolType
    start_line: int
    end_line: int
    code: str


@dataclass(frozen=True)
class CodeChunk:
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

    def to_properties(self) -> dict:
        return asdict(self)
