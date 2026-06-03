from __future__ import annotations

import re


SYNONYMS = {
    "тариф": ["расчет тарифа", "стоимость", "ставка", "цена", "расчет стоимости"],
    "груз": ["отправление", "перевозка", "заявка", "накладная"],
    "температурный": ["температурный режим", "температура", "рефрижератор"],
    "клиент": ["контрагент", "плательщик", "заказчик"],
    "ттн": ["транспортная накладная", "печатная форма", "накладная"],
    "печать": ["печатная форма", "макет", "форма печати"],
    "проведение": ["ОбработкаПроведения", "движения", "регистры"],
}


def expand_query(query: str) -> str:
    lower_query = query.lower()
    additions: list[str] = []
    seen: set[str] = set()
    for trigger, synonyms in SYNONYMS.items():
        if not _matches_trigger(lower_query, trigger):
            continue
        for synonym in synonyms:
            key = synonym.lower()
            if key not in seen and key not in lower_query:
                seen.add(key)
                additions.append(synonym)
    if not additions:
        return query
    return f"{query}\nСинонимы: {', '.join(additions)}"


def _matches_trigger(lower_query: str, trigger: str) -> bool:
    if trigger in lower_query:
        return True
    stem = _rough_stem(trigger)
    if len(stem) < 4:
        return False
    return any(token.startswith(stem) for token in re.findall(r"[а-яa-z0-9_]+", lower_query))


def _rough_stem(word: str) -> str:
    for suffix in ("ный", "ний", "ого", "его", "ая", "ое", "ые", "ых", "ие", "ия", "ом", "ам", "а", "у", "ы", "и", "е"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word
