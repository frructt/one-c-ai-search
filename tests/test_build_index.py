from common.models import CodeChunk
from indexer.build_index import IndexStats, _flush, print_stats
from indexer.embedder_client import EmbeddingError
from indexer.weaviate_writer import WeaviateWriteError


class FailingEmbedder:
    def embed_batch(self, texts):
        raise EmbeddingError("embed down")


class WorkingEmbedder:
    def embed_batch(self, texts):
        return [[0.1, 0.2] for _ in texts]


class UnusedWriter:
    def write_chunks(self, chunks, vectors):
        raise AssertionError("writer should not be called")


class FailingWriter:
    def write_chunks(self, chunks, vectors):
        raise WeaviateWriteError("write down")


def test_flush_records_embedding_failures():
    stats = IndexStats()

    _flush([chunk("src/a.bsl", "A")], FailingEmbedder(), UnusedWriter(), stats)

    assert stats.embedding_errors == 1
    assert stats.failures[0].stage == "embedding"
    assert stats.failures[0].path == "src/a.bsl"
    assert stats.failures[0].symbol_name == "A"


def test_flush_records_weaviate_failures():
    stats = IndexStats()

    _flush([chunk("src/b.bsl", "B")], WorkingEmbedder(), FailingWriter(), stats)

    assert stats.weaviate_errors == 1
    assert stats.failures[0].stage == "weaviate_write"
    assert stats.failures[0].path == "src/b.bsl"


def test_print_stats_outputs_failure_report(capsys):
    stats = IndexStats(files_scanned=1, files_failed=1)
    stats.record_failure(stage="read_or_parse", path="src/broken.bsl", message="bad utf-8")

    print_stats(stats)

    output = capsys.readouterr().out
    assert "Indexing failures:" in output
    assert "stage=read_or_parse" in output
    assert "src/broken.bsl" in output


def chunk(path: str, symbol_name: str) -> CodeChunk:
    return CodeChunk(
        repo="gp",
        branch="master",
        path=path,
        gitlab_url=f"https://gitlab/{path}",
        module_name="Module",
        object_name="Module",
        object_type="CommonModule",
        symbol_name=symbol_name,
        symbol_type="function",
        start_line=1,
        end_line=2,
        code="Функция A()\nКонецФункции",
        identifiers=[],
        search_text="Функция A",
        chunk_id=f"{path}:{symbol_name}",
        source_commit="abc",
        indexed_at="2026-06-10T00:00:00+00:00",
        content_hash="hash",
    )
