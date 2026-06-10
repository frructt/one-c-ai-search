# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python 3.11 proof of concept for finding likely 1C BSL change locations. Core packages live at the repository root:

- `api/`: FastAPI app, request/response schemas, search orchestration, query expansion, reranking, and Weaviate search.
- `indexer/`: BSL parsing, chunk construction, embedding calls, Git metadata, and Weaviate writes.
- `common/`: shared settings, logging, models, OpenAI-compatible response helpers, and Weaviate connection setup.
- `eval/`: CSV-based search quality evaluation.
- `openwebui_tool/`: OpenWebUI integration wrapper.
- `tests/`: offline pytest suite using fakes for external services.

Keep new code in the package that owns the behavior. Avoid adding more generic top-level packages when an existing package fits.

## Build, Test, and Development Commands

Run commands from this project root:

```bash
cd onec-code-search
pip install -e .
python -m pytest
```

`pip install -e .` installs the local package and dependencies. `python -m pytest` runs the unit test suite.

Service-dependent commands require a configured `.env` and reachable external services:

```bash
python -m indexer.build_index
uvicorn api.app:app --host 0.0.0.0 --port 8000
python -m eval.run_eval --tasks eval/eval_tasks.csv --api-url http://localhost:8000
```

## Coding Style & Naming Conventions

Use Python 3.11+ style with 4-space indentation, type hints, explicit dataclasses for internal records, and Pydantic models for API schemas. Prefer clear control flow and explicit error classes over clever abstractions. Reuse `common.settings.Settings`, shared clients, and existing response/model helpers before introducing new wrappers.

Name tests as `tests/test_*.py`. Keep function and variable names descriptive; BSL-domain text may use Russian identifiers where that matches existing fixtures or user-facing output.

## Testing Guidelines

Tests should be fast, deterministic, and offline by default. Mock or fake Weaviate, embedding, and LLM clients instead of requiring live services. Add focused tests for new ranking logic, API mapping, settings behavior, indexer failure handling, and edge cases. Manual indexing, API search, and evaluation runs are useful follow-up checks when changing service integration.

## Commit & Pull Request Guidelines

Use short imperative, sentence-case commit summaries, matching the current history, for example `Fix Weaviate score fallback`. Pull requests should describe behavior changes, configuration impact, external-service assumptions, and test results. Link related issues or tasks when available; include screenshots only for OpenWebUI-facing changes.

## Configuration & External Services

Copy `.env.example` to `.env` for local service work. Key settings include `REPO_PATH`, `WEAVIATE_URL`, `EMBEDDINGS_BASE_URL`, optional `LLM_*` values, `SEARCH_INTERNAL_LIMIT`, and `API_MAX_LIMIT`. Keep search and batch limits conservative unless testing against realistic service capacity.
