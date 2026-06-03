from __future__ import annotations

from pydantic import BaseModel, Field


class FindChangePlacesRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Описание задачи аналитика")
    repo: str = Field("gp", min_length=1)
    branch: str = Field("master", min_length=1)
    limit: int = Field(10, ge=1)


class CandidateResponse(BaseModel):
    rank: int
    path: str
    gitlab_url: str
    module_name: str
    object_type: str
    symbol_name: str
    symbol_type: str
    start_line: int
    end_line: int
    score: float
    final_score: float
    why: list[str]
    code_preview: str


class FindChangePlacesResponse(BaseModel):
    query: str
    expanded_query: str
    repo: str
    branch: str
    candidates: list[CandidateResponse]
