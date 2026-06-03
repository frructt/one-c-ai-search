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
