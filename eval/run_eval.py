from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass(frozen=True)
class EvalTask:
    task_id: str
    task_text: str
    expected_files: list[str]


@dataclass(frozen=True)
class EvalResult:
    task_id: str
    rank: int | None
    expected_found: bool


def read_tasks(path: Path) -> list[EvalTask]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        tasks = []
        for row in reader:
            expected_files = [
                item.strip()
                for item in row["expected_files"].split(";")
                if item.strip()
            ]
            tasks.append(
                EvalTask(
                    task_id=row["task_id"],
                    task_text=row["task_text"],
                    expected_files=expected_files,
                )
            )
    return tasks


def candidate_rank(candidates: list[dict], expected_files: list[str]) -> int | None:
    expected = set(expected_files)
    for index, candidate in enumerate(candidates, start=1):
        if candidate.get("path") in expected:
            return index
    return None


def compute_hits(results: list[EvalResult]) -> dict[str, float | int]:
    total = len(results)
    hit5 = sum(1 for result in results if result.rank is not None and result.rank <= 5)
    hit10 = sum(1 for result in results if result.rank is not None and result.rank <= 10)
    return {
        "tasks": total,
        "hit5": hit5,
        "hit10": hit10,
        "hit5_pct": (hit5 / total * 100.0) if total else 0.0,
        "hit10_pct": (hit10 / total * 100.0) if total else 0.0,
    }


def run_eval(
    *,
    tasks: list[EvalTask],
    api_url: str,
    repo: str,
    branch: str,
    limit: int,
    timeout: int,
) -> list[EvalResult]:
    results: list[EvalResult] = []
    endpoint = f"{api_url.rstrip('/')}/find-change-places"
    for task in tasks:
        response = requests.post(
            endpoint,
            json={
                "query": task.task_text,
                "repo": repo,
                "branch": branch,
                "limit": limit,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        rank = candidate_rank(data.get("candidates", []), task.expected_files)
        results.append(EvalResult(task_id=task.task_id, rank=rank, expected_found=rank is not None))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Hit@5 and Hit@10 for 1C code search.")
    parser.add_argument("--tasks", default="eval/eval_tasks.csv", help="Path to eval CSV")
    parser.add_argument("--api-url", default="http://localhost:8000", help="FastAPI base URL")
    parser.add_argument("--repo", default="gp")
    parser.add_argument("--branch", default="master")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    tasks = read_tasks(Path(args.tasks))
    results = run_eval(
        tasks=tasks,
        api_url=args.api_url,
        repo=args.repo,
        branch=args.branch,
        limit=args.limit,
        timeout=args.timeout,
    )
    metrics = compute_hits(results)
    print(f"Tasks: {metrics['tasks']}")
    print(f"Hit@5: {metrics['hit5']}/{metrics['tasks']} = {metrics['hit5_pct']:.1f}%")
    print(f"Hit@10: {metrics['hit10']}/{metrics['tasks']} = {metrics['hit10_pct']:.1f}%")
    print()
    print("Misses:")
    for result in results:
        if result.rank is None:
            print(f"- task_id={result.task_id}: expected file not found")
        elif result.rank > 10:
            print(f"- task_id={result.task_id}: expected file rank > 10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
