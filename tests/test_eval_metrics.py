from eval.run_eval import EvalResult, candidate_rank, compute_hits


def test_candidate_rank_finds_expected_file():
    candidates = [{"path": "a.bsl"}, {"path": "b.bsl"}]

    assert candidate_rank(candidates, ["b.bsl"]) == 2


def test_compute_hits():
    metrics = compute_hits(
        [
            EvalResult(task_id="1", rank=3, expected_found=True),
            EvalResult(task_id="2", rank=9, expected_found=True),
            EvalResult(task_id="3", rank=None, expected_found=False),
        ]
    )

    assert metrics["tasks"] == 3
    assert metrics["hit5"] == 1
    assert metrics["hit10"] == 2
