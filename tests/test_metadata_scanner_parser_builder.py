from pathlib import Path

from common.settings import Settings
from indexer.metadata_builder import build_metadata_object
from indexer.metadata_parser import local_name, parse_metadata_xml
from indexer.metadata_scanner import classify_xml_path, scan_metadata_xml


def test_classify_known_and_unknown_xml(tmp_path):
    repo_path = tmp_path / "repo"
    known = repo_path / "src" / "configuration" / "Documents" / "Заявка" / "Заявка.xml"
    unknown = repo_path / "src" / "configuration" / "UnknownFolder" / "X.xml"
    known.parent.mkdir(parents=True)
    unknown.parent.mkdir(parents=True)
    known.write_text("<Document/>", encoding="utf-8")
    unknown.write_text("<Unknown/>", encoding="utf-8")

    scan = scan_metadata_xml(repo_path)

    assert len(scan.known_xml) == 1
    assert len(scan.unknown_xml) == 1
    assert scan.known_xml[0].object_name == "Заявка"
    assert scan.known_xml[0].object_type == "Document"


def test_classify_common_module_without_configuration_folder(tmp_path):
    repo_path = tmp_path / "repo"
    path = repo_path / "src" / "CommonModules" / "РасчетТарифов" / "РасчетТарифов.xml"
    path.parent.mkdir(parents=True)
    path.write_text("<CommonModule/>", encoding="utf-8")

    scanned = classify_xml_path(path, repo_path)

    assert scanned.known is True
    assert scanned.object_dir == "src/CommonModules/РасчетТарифов"
    assert scanned.object_type == "CommonModule"


def test_parse_metadata_xml_ignores_namespaces(tmp_path):
    path = tmp_path / "doc.xml"
    path.write_text(
        """
        <md:Document xmlns:md="urn:test">
          <md:Synonym>Заявка на перевозку</md:Synonym>
          <md:Comment>Документ перевозки</md:Comment>
          <md:Attributes>
            <md:Attribute>
              <md:Name>ТемпературныйРежим</md:Name>
              <md:Synonym>Температурный режим</md:Synonym>
            </md:Attribute>
          </md:Attributes>
          <md:TabularSections>
            <md:TabularSection>
              <md:Name>Грузы</md:Name>
            </md:TabularSection>
          </md:TabularSections>
          <md:Forms>
            <md:Form name="ФормаДокумента"/>
          </md:Forms>
          <md:Commands>
            <md:Command>
              <md:Name>ПересчитатьТариф</md:Name>
            </md:Command>
          </md:Commands>
        </md:Document>
        """,
        encoding="utf-8",
    )

    parsed = parse_metadata_xml(path)

    assert local_name("{urn:test}Document") == "Document"
    assert parsed.synonym == "Заявка на перевозку"
    assert parsed.comment == "Документ перевозки"
    assert parsed.attributes == ["ТемпературныйРежим / Температурный режим"]
    assert parsed.tabular_sections == ["Грузы"]
    assert parsed.forms == ["ФормаДокумента"]
    assert parsed.commands == ["ПересчитатьТариф"]


def test_build_metadata_object_links_bsl_paths_and_search_text(tmp_path):
    repo_path = tmp_path / "repo"
    object_dir = repo_path / "src" / "configuration" / "Documents" / "Заявка"
    object_dir.mkdir(parents=True)
    xml_path = object_dir / "Заявка.xml"
    module_path = object_dir / "Ext" / "ObjectModule.bsl"
    form_module = object_dir / "Forms" / "ФормаДокумента" / "Ext" / "Form" / "Module.bsl"
    module_path.parent.mkdir(parents=True)
    form_module.parent.mkdir(parents=True)
    xml_path.write_text("<Document><Synonym>Заявка</Synonym></Document>", encoding="utf-8")
    module_path.write_text("Процедура A()\nКонецПроцедуры", encoding="utf-8")
    form_module.write_text("Процедура B()\nКонецПроцедуры", encoding="utf-8")
    scanned = classify_xml_path(xml_path, repo_path)
    parsed = parse_metadata_xml(xml_path)

    metadata_object = build_metadata_object(
        repo="gp",
        branch="master",
        repo_path=repo_path,
        scanned_xml=[scanned],
        parsed_files=[parsed],
        settings=settings(repo_path),
        source_commit="abc",
        indexed_at="2026-06-10T00:00:00+00:00",
    )

    assert metadata_object.path == "src/configuration/Documents/Заявка"
    assert metadata_object.synonym == "Заявка"
    assert metadata_object.related_bsl_paths == [
        "src/configuration/Documents/Заявка/Ext/ObjectModule.bsl",
        "src/configuration/Documents/Заявка/Forms/ФормаДокумента/Ext/Form/Module.bsl",
    ]
    assert "Синоним: Заявка" in metadata_object.search_text
    assert metadata_object.metadata_id
    assert metadata_object.content_hash


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
