from __future__ import annotations

from typing import Any


_MISSING = object()


def response_field(value: Any, name: str, default: Any = _MISSING):
    if isinstance(value, dict):
        if default is _MISSING:
            return value[name]
        return value.get(name, default)
    if default is _MISSING:
        return getattr(value, name)
    return getattr(value, name, default)
