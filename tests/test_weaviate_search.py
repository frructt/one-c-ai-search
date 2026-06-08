from types import SimpleNamespace

from api.weaviate_search import _metadata_score


def test_metadata_score_keeps_positive_float():
    metadata = SimpleNamespace(score=0.42)

    assert _metadata_score(metadata, rank=3, total=10) == 0.42


def test_metadata_score_keeps_positive_string():
    metadata = SimpleNamespace(score="0.73")

    assert _metadata_score(metadata, rank=3, total=10) == 0.73


def test_metadata_score_falls_back_when_none():
    metadata = SimpleNamespace(score=None)

    assert _metadata_score(metadata, rank=1, total=10) == 1.0


def test_metadata_score_falls_back_when_zero():
    metadata = SimpleNamespace(score=0)

    assert _metadata_score(metadata, rank=10, total=10) == 0.01


def test_metadata_score_falls_back_when_invalid():
    metadata = SimpleNamespace(score="not-a-number")

    assert _metadata_score(metadata, rank=2, total=3) == 0.505
