# onec-code-search

Proof-of-concept поиска вероятных мест изменения в большом 1С-репозитории.

Пользователь вводит текст задачи аналитика, backend ищет релевантные `.bsl` процедуры/функции в Weaviate и возвращает top-N кандидатов с GitLab-ссылкой и кратким объяснением.

## Repository layout

PoC должен лежать отдельно от 1С-кода. Ожидаемый сценарий:

```text
workspace/
  onec-code-search/
  1С ГП/
    gp_bsl/
      src/
```

В `.env.example` это отражено так:

```env
REPO_PATH=../1С ГП/gp_bsl
```

## Setup

```bash
cp .env.example .env
pip install -e .
```

Проверьте в `.env`:

- `REPO_PATH` указывает на директорию с `src`;
- `GITLAB_BASE_URL` и `GITLAB_PROJECT_PATH` соответствуют проекту;
- `WEAVIATE_URL` и `EMBEDDINGS_BASE_URL` доступны из окружения, где запускается PoC.

## Indexing

```bash
python -m indexer.build_index
```

Индексатор:

- ищет все `.bsl` в `REPO_PATH`;
- режет файлы на процедуры/функции;
- строит `search_text`;
- получает embeddings через OpenAI-compatible `/v1/embeddings`;
- создает collection `OneCCodeChunk`, если ее еще нет;
- пишет chunks и self-provided vectors в Weaviate.

## API

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Search:

```bash
curl -X POST http://localhost:8000/find-change-places \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Нужно поменять расчет тарифа для температурного груза",
    "repo": "gp",
    "branch": "master",
    "limit": 10
  }'
```

## OpenWebUI Tool

Добавьте содержимое `openwebui_tool/find_change_places_tool.py` как Tool в OpenWebUI.

Backend URL можно переопределить:

```env
ONEC_CODE_SEARCH_API_URL=http://onec-code-search-api:8000
```

## Evaluation

Создайте `eval/eval_tasks.csv` по примеру:

```bash
cp eval/eval_tasks.csv.example eval/eval_tasks.csv
```

Запуск:

```bash
python -m eval.run_eval --tasks eval/eval_tasks.csv --api-url http://localhost:8000
```

Скрипт считает Hit@5 и Hit@10 и выводит промахи.

## Tests

```bash
pytest
```

Unit-тесты не требуют живого Weaviate или embedding endpoint.

## Future work

- LLM query expansion вместо словаря;
- индексация XML metadata;
- git blame и последние коммиты;
- поиск похожих MR;
- граф зависимостей процедур и модулей;
- отдельный reranker;
- impact analysis;
- автогенерация плана изменения;
- поддержка нескольких веток;
- инкрементальная индексация по git diff.
