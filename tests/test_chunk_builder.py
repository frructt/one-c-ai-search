from pathlib import Path

from common.models import SymbolChunk
from common.settings import Settings
from indexer.chunk_builder import build_chunk, extract_identifiers, parse_1c_path


def settings(tmp_path: Path) -> Settings:
    return Settings(
        repo_name="gp",
        repo_path=tmp_path,
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
        embeddings_model="qwen3-embedder-8b",
        embedding_batch_size=16,
        embedding_text_limit=16000,
        embedding_timeout_seconds=30,
        embedding_retries=3,
        search_alpha=0.35,
        search_internal_limit=50,
        search_internal_limit_max=200,
        api_default_limit=10,
        api_max_limit=50,
        api_host="0.0.0.0",
        api_port=8000,
    )


def test_parse_common_module_path():
    module_name, object_name, object_type = parse_1c_path(
        "src/CommonModules/РасчетТарифовСервер/Ext/Module.bsl"
    )

    assert module_name == "РасчетТарифовСервер"
    assert object_name == "РасчетТарифовСервер"
    assert object_type == "CommonModule"


def test_parse_form_path():
    module_name, object_name, object_type = parse_1c_path(
        "src/configuration/Documents/ЗаявкаНаПеревозку/Forms/ФормаДокумента/Ext/Form/Module.bsl"
    )

    assert module_name == "ЗаявкаНаПеревозку.ФормаДокумента"
    assert object_name == "ЗаявкаНаПеревозку"
    assert object_type == "Form"


def test_parse_common_command_from_screenshot_shape():
    module_name, object_name, object_type = parse_1c_path(
        "src/configuration/CommonCommands/АудиторскийСлед/Ext/CommandModule.bsl"
    )

    assert module_name == "АудиторскийСлед"
    assert object_name == "АудиторскийСлед"
    assert object_type == "CommonCommand"


def test_extract_identifiers_unique_and_keeps_russian():
    identifiers = extract_identifiers("Процедура X()\nТариф = Груз.ТемпературныйРежим;\nТариф = 2;\n")

    assert identifiers == ["Тариф", "Груз", "ТемпературныйРежим"]


def test_build_chunk_contract(tmp_path):
    repo_path = tmp_path / "gp_bsl"
    path = repo_path / "src" / "CommonModules" / "РасчетТарифовСервер" / "Ext" / "Module.bsl"
    path.parent.mkdir(parents=True)
    symbol = SymbolChunk(
        symbol_name="РассчитатьСтоимость",
        symbol_type="function",
        start_line=10,
        end_line=12,
        code="Функция РассчитатьСтоимость()\nВозврат Тариф;\nКонецФункции",
    )

    chunk = build_chunk(
        repo="gp",
        branch="master",
        path=path,
        repo_path=repo_path,
        symbol=symbol,
        settings=settings(repo_path),
        source_commit="abc123",
        indexed_at="2026-06-03T00:00:00+00:00",
    )

    assert chunk.path == "src/CommonModules/РасчетТарифовСервер/Ext/Module.bsl"
    assert chunk.gitlab_url.endswith("/src/CommonModules/%D0%A0%D0%B0%D1%81%D1%87%D0%B5%D1%82%D0%A2%D0%B0%D1%80%D0%B8%D1%84%D0%BE%D0%B2%D0%A1%D0%B5%D1%80%D0%B2%D0%B5%D1%80/Ext/Module.bsl#L10")
    assert chunk.source_commit == "abc123"
    assert chunk.content_hash
    assert chunk.chunk_id
    assert "Репозиторий: gp" in chunk.search_text
    assert "Символ: РассчитатьСтоимость" in chunk.search_text
