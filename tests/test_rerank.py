from api.rerank import build_why, rank_files, rerank
from api.search_models import MetadataCandidate, SearchCandidate


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


def test_metadata_boost_can_lift_linked_file_and_add_evidence():
    linked = candidate(path="src/doc.bsl", score=0.65)
    unlinked = candidate(path="src/common.bsl", score=0.70)
    metadata = metadata_candidate(related_bsl_paths=["src/doc.bsl"], score=1.0)

    ranked = rank_files(
        [linked, unlinked],
        "температурный груз",
        metadata_hits=[metadata],
        metadata_boost_max=0.25,
    )

    assert ranked[0].path == "src/doc.bsl"
    assert ranked[0].metadata_boost > 0
    assert any("метаданные" in reason for reason in build_why(ranked[0], "температурный груз"))


def test_unlinked_metadata_does_not_boost_file():
    linked = candidate(path="src/doc.bsl", score=0.65)
    unlinked = candidate(path="src/common.bsl", score=0.70)
    metadata = metadata_candidate(related_bsl_paths=["src/other.bsl"], score=1.0)

    ranked = rank_files(
        [linked, unlinked],
        "температурный груз",
        metadata_hits=[metadata],
        metadata_boost_max=0.25,
    )

    assert ranked[0].path == "src/common.bsl"
    assert ranked[0].metadata_boost == 0


def test_archive_penalty_still_applies_after_metadata_boost():
    archived = candidate(path="src/archive/doc.bsl", score=0.70)
    current = candidate(path="src/current/doc.bsl", score=0.70)
    metadata = metadata_candidate(related_bsl_paths=["src/archive/doc.bsl"], score=1.0)

    ranked = rank_files(
        [archived, current],
        "температурный груз",
        metadata_hits=[metadata],
        metadata_boost_max=0.25,
    )

    assert ranked[0].path == "src/current/doc.bsl"


def candidate(path: str, score: float) -> SearchCandidate:
    return SearchCandidate(
        repo="gp",
        branch="master",
        path=path,
        gitlab_url=f"https://gitlab/{path}",
        module_name="Module",
        object_name="Module",
        object_type="CommonModule",
        symbol_name="Рассчитать",
        symbol_type="function",
        start_line=1,
        end_line=5,
        code="Функция Рассчитать()\nКонецФункции",
        identifiers=[],
        search_text="Рассчитать",
        chunk_id=path,
        source_commit="abc",
        indexed_at="2026-06-10T00:00:00+00:00",
        content_hash="hash",
        score=score,
        final_score=score,
        retrieval_profiles=("balanced",),
        original_rank=1,
    )


def metadata_candidate(*, related_bsl_paths: list[str], score: float) -> MetadataCandidate:
    return MetadataCandidate(
        repo="gp",
        branch="master",
        path="src/configuration/Documents/Заявка",
        object_name="Заявка",
        object_type="Document",
        synonym="Заявка на перевозку",
        comment="",
        attributes=["ТемпературныйРежим"],
        tabular_sections=[],
        forms=[],
        commands=[],
        related_bsl_paths=related_bsl_paths,
        search_text="Заявка",
        metadata_id="meta-1",
        source_commit="abc",
        indexed_at="2026-06-10T00:00:00+00:00",
        content_hash="hash",
        score=score,
        original_rank=1,
    )
