from api.rerank import build_why, rerank


def test_symbol_match_gets_bonus():
    items = [
        {"score": 0.5, "symbol_name": "НеТо", "module_name": "", "identifiers": [], "path": "src/a.bsl", "symbol_type": "function"},
        {"score": 0.5, "symbol_name": "РассчитатьТариф", "module_name": "", "identifiers": [], "path": "src/b.bsl", "symbol_type": "function"},
    ]

    ranked = rerank(items, "поменять тариф")

    assert ranked[0]["symbol_name"] == "РассчитатьТариф"
    assert ranked[0]["final_score"] > ranked[1]["final_score"]


def test_archive_path_penalty():
    items = [
        {"score": 0.7, "symbol_name": "Тариф", "path": "src/archive/tariff.bsl", "symbol_type": "function"},
        {"score": 0.7, "symbol_name": "Тариф", "path": "src/current/tariff.bsl", "symbol_type": "function"},
    ]

    ranked = rerank(items, "тариф")

    assert ranked[0]["path"] == "src/current/tariff.bsl"


def test_module_result_penalty_when_concrete_exists():
    items = [
        {"score": 0.7, "symbol_name": "<module>", "path": "src/a.bsl", "symbol_type": "module"},
        {"score": 0.7, "symbol_name": "Рассчитать", "path": "src/b.bsl", "symbol_type": "function"},
    ]

    ranked = rerank(items, "рассчитать")

    assert ranked[0]["symbol_type"] == "function"


def test_build_why_returns_reasons():
    item = {
        "symbol_name": "РассчитатьТариф",
        "module_name": "РасчетТарифовСервер",
        "identifiers": ["ТемпературныйРежим"],
        "path": "src/CommonModules/РасчетТарифовСервер/Ext/Module.bsl",
        "symbol_type": "function",
    }

    reasons = build_why(item, "тариф температурный")

    assert reasons
    assert len(reasons) <= 5
    assert any("тариф" in reason for reason in reasons)
