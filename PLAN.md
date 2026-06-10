# PoC plan

This repository implements the approved proof-of-concept from the parent `PLAN.md`:

1. Index `.bsl` files from a sibling 1C repository.
2. Split code by procedure/function with module fallback.
3. Build typed chunks and external embeddings.
4. Store chunks and vectors in Weaviate.
5. Serve `/find-change-places` from FastAPI.
6. Expose an OpenWebUI Tool.
7. Measure Hit@5 and Hit@10 with `eval/run_eval.py`.

Accepted implementation adjustments:

- `REPO_PATH` defaults to `../1С ГП/gp_bsl`.
- Shared `common/settings.py` validates configuration.
- Chunks include `source_commit`, `indexed_at`, and `content_hash`.
- Weaviate collection is created by the indexer and uses self-provided vectors.
- Embeddings and Weaviate uploads are batched.
- Unit tests avoid requiring live Weaviate or embedding services.

## Metadata XML Roadmap

Next accepted implementation phase:

1. Start with a metadata scanner because the real XML layout differs between 1C exports.
2. Scan `REPO_PATH` for `*.xml`, classify known 1C object folders, and report unknown XML without failing the run.
3. Parse metadata XML with `xml.etree.ElementTree`, ignoring XML namespaces by local tag name.
4. Build `MetadataObject` records with object name/type, synonym, comment, attributes, tabular sections, forms, commands, related BSL paths, and `search_text`.
5. Store metadata in a separate Weaviate collection: `OneCMetadataObject`.
6. Keep `OneCCodeChunk` unchanged.
7. Search metadata before BSL search and boost linked `.bsl` files in file-level ranking.
8. Add metadata evidence to candidate explanations.

Out of scope for this phase:

- Confluence indexing;
- legacy `bin` indexing beyond inventory/reporting;
- full 1C dependency graph;
- full BSL AST parser.
