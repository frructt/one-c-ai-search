from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from api.schemas import FindChangePlacesRequest, FindChangePlacesResponse
from api.search_service import EmbeddingError, SearchService, WeaviateSearchError
from common.logging import configure_logging
from common.settings import load_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = load_settings()
    app.state.search_service = SearchService(settings)
    try:
        yield
    finally:
        app.state.search_service.close()


app = FastAPI(title="1C Code Search PoC", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search", response_model=FindChangePlacesResponse)
def search(request: FindChangePlacesRequest) -> FindChangePlacesResponse:
    return find_change_places(request)


@app.post("/find-change-places", response_model=FindChangePlacesResponse)
def find_change_places(request: FindChangePlacesRequest) -> FindChangePlacesResponse:
    service: SearchService = app.state.search_service
    try:
        return service.find_change_places(
            query=request.query,
            repo=request.repo,
            branch=request.branch,
            limit=request.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except WeaviateSearchError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
