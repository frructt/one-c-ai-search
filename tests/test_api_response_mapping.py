from api.search_service import build_candidate_response, make_code_preview


def test_code_preview_truncates_full_code():
    code = "x" * 2000

    preview = make_code_preview(code, limit=100)

    assert len(preview) < len(code)
    assert preview.endswith("... [truncated]")


def test_candidate_response_does_not_include_full_code():
    item = {
        "path": "src/a.bsl",
        "gitlab_url": "https://gitlab/a",
        "module_name": "Модуль",
        "object_type": "CommonModule",
        "symbol_name": "Функция",
        "symbol_type": "function",
        "start_line": 1,
        "end_line": 2,
        "score": 0.5,
        "final_score": 0.6,
        "code": "x" * 2000,
    }

    candidate = build_candidate_response(rank=1, item=item, query="модуль")

    assert candidate.rank == 1
    assert len(candidate.code_preview) < 2000
    assert not hasattr(candidate, "code")
