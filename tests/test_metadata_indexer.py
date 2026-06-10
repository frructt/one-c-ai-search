from pathlib import Path

from common.settings import Settings
from indexer.metadata_indexer import MetadataIndexStats, index_metadata, print_metadata_stats


class WorkingEmbedder:
    def embed_batch(self, texts):
        return [[0.1, 0.2] for _ in texts]


class CapturingWriter:
    def __init__(self):
        self.objects = []
        self.vectors = []

    def write_metadata_objects(self, objects, vectors):
        self.objects.extend(objects)
        self.vectors.extend(vectors)
        return len(objects)


def test_index_metadata_reports_unknown_xml_without_failing(tmp_path):
    repo_path = tmp_path / "repo"
    known = repo_path / "src" / "configuration" / "Documents" / "Заявка" / "Заявка.xml"
    unknown = repo_path / "src" / "configuration" / "UnknownFolder" / "X.xml"
    bsl = repo_path / "src" / "configuration" / "Documents" / "Заявка" / "Ext" / "ObjectModule.bsl"
    known.parent.mkdir(parents=True)
    unknown.parent.mkdir(parents=True)
    bsl.parent.mkdir(parents=True)
    known.write_text("<Document><Synonym>Заявка</Synonym></Document>", encoding="utf-8")
    unknown.write_text("<Unknown/>", encoding="utf-8")
    bsl.write_text("Процедура A()\nКонецПроцедуры", encoding="utf-8")
    writer = CapturingWriter()

    stats = index_metadata(
        settings=settings(repo_path),
        embedder=WorkingEmbedder(),
        writer=writer,
        source_commit="abc",
    )

    assert stats.files_scanned == 2
    assert stats.known_xml == 1
    assert stats.unknown_xml == 1
    assert stats.files_failed == 0
    assert stats.objects_created == 1
    assert stats.objects_uploaded == 1
    assert stats.unknown_xml_paths == ["src/configuration/UnknownFolder/X.xml"]
    assert writer.objects[0].synonym == "Заявка"


def test_index_metadata_records_malformed_known_xml(tmp_path):
    repo_path = tmp_path / "repo"
    known = repo_path / "src" / "configuration" / "Documents" / "Заявка" / "Заявка.xml"
    known.parent.mkdir(parents=True)
    known.write_text("<Document>", encoding="utf-8")

    stats = index_metadata(
        settings=settings(repo_path),
        embedder=WorkingEmbedder(),
        writer=CapturingWriter(),
        source_commit="abc",
    )

    assert stats.files_failed == 1
    assert stats.failures[0].stage == "parse_metadata_xml"
    assert stats.objects_created == 1


def test_print_metadata_stats_outputs_unknown_xml(capsys):
    stats = MetadataIndexStats(files_scanned=1, unknown_xml=1)
    stats.unknown_xml_paths.append("src/unknown.xml")

    print_metadata_stats(stats)

    output = capsys.readouterr().out
    assert "Unknown XML files:" in output
    assert "src/unknown.xml" in output


def settings(repo_path: Path) -> Settings:
    return Settings(
        repo_name="gp",
        repo_path=repo_path,
        branch="master",
        allowed_repos=["gp"],
        allowed_branches=["master"],
        gitlab_base_url="https://gitlab.company.ru",
        gitlab_project_path="group/project",
        weaviate_url="http://localhost:8080",
        weaviate_api_key=None,
        weaviate_grpc_host=None,
        weaviate_grpc_port=50051,
        weaviate_grpc_secure=False,
        weaviate_collection="OneCCodeChunk",
        weaviate_vector_name="code_vector",
        weaviate_batch_size=64,
        embeddings_base_url="http://localhost:8001/v1",
        embeddings_api_key="test-key",
        embeddings_model="qwen3-embedder-8b",
        embedding_batch_size=16,
        embedding_text_limit=16000,
        embedding_timeout_seconds=30,
        embedding_retries=3,
        llm_query_expansion_enabled=False,
        llm_base_url="http://localhost:8002/v1",
        llm_api_key="test-key",
        llm_model="qwen2.5-coder-32b-instruct",
        llm_timeout_seconds=10,
        llm_retries=1,
        llm_max_tokens=512,
        search_alpha=0.35,
        search_internal_limit=50,
        search_internal_limit_max=200,
        indexer_fail_on_failed_files=True,
        api_default_limit=10,
        api_max_limit=50,
        api_host="0.0.0.0",
        api_port=8000,
    )
