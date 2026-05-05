from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from langsmith import Client, evaluate

from resolver.graph import build_graph


def _load_dataset() -> list[dict[str, Any]]:
    dataset = Path("evals/dataset.jsonl")
    return [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]


def _prepare_eval_workspace(source_repo: str) -> str:
    temp_dir = Path(tempfile.mkdtemp(prefix="resolver-eval-", dir=".work"))
    repo_dir = temp_dir / "repo"

    def _ignore(_path: str, names: list[str]) -> set[str]:
        ignored = {".git", ".venv", ".work", ".chroma", "__pycache__", ".pytest_cache", ".mypy_cache"}
        return {name for name in names if name in ignored}

    shutil.copytree(source_repo, repo_dir, ignore=_ignore)
    return str(repo_dir)


def target(inputs: dict[str, Any]) -> dict[str, Any]:
    graph = build_graph()
    local_path = _prepare_eval_workspace(inputs.get("local_path", "."))
    state = graph.invoke(
        {
            "issue": {
                "repo": inputs["repo"],
                "number": int(inputs["issue_number"]),
                "title": inputs.get("title", f"Issue {inputs['issue_number']}"),
                "body": inputs.get("body", ""),
                "local_path": local_path,
            },
            "test_result": "unrun",
            "retries": 0,
            "errors": [],
            "run_dir": ".work/evals",
        },
        config={"configurable": {"thread_id": f"eval-{inputs['issue_number']}"}},
    )
    return {
        "test_result": state.get("test_result", "fail"),
        "patch": state.get("patch", ""),
        "pr_url": state.get("pr_url", ""),
    }


def tests_pass(outputs: dict[str, Any], reference_outputs: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"key": "tests_pass", "score": 1 if outputs.get("test_result") == "pass" else 0}


def patch_similarity(
    outputs: dict[str, Any], reference_outputs: dict[str, Any] | None = None
) -> dict[str, Any]:
    gold = (reference_outputs or {}).get("expected_patch", "")
    got = outputs.get("patch", "")
    if not gold or not got:
        score = 0.0
    else:
        overlap = len(set(gold.split()) & set(got.split()))
        score = overlap / max(1, len(set(gold.split())))
    return {"key": "patch_similarity", "score": round(score, 3)}


def _run_local_eval(examples: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in examples:
        outputs = target(row)
        tp = tests_pass(outputs)["score"]
        ps = patch_similarity(outputs, {"expected_patch": row["expected_patch"]})["score"]
        rows.append({"issue_number": row["issue_number"], "tests_pass": tp, "patch_similarity": ps})
    tests_pass_rate = sum(r["tests_pass"] for r in rows) / len(rows)
    patch_similarity_avg = sum(r["patch_similarity"] for r in rows) / len(rows)
    return {
        "mode": "local",
        "cases": len(rows),
        "tests_pass_rate": round(tests_pass_rate, 3),
        "patch_similarity_avg": round(patch_similarity_avg, 3),
        "rows": rows,
    }


def _run_langsmith_eval(examples: list[dict[str, Any]]) -> dict[str, Any]:
    client = Client()
    dataset_name = f"issue-resolver-local-eval-{os.getpid()}"
    dataset = client.create_dataset(dataset_name=dataset_name, description="Local toy issue resolver evals")
    client.create_examples(
        inputs=[
            {
                "repo": row["repo"],
                "issue_number": row["issue_number"],
                "title": row["title"],
                "body": row["body"],
                "local_path": row["local_path"],
            }
            for row in examples
        ],
        outputs=[{"expected_patch": row["expected_patch"]} for row in examples],
        dataset_id=dataset.id,
    )
    results: Any = evaluate(
        target,
        data=dataset.id,
        evaluators=[tests_pass, patch_similarity],
        experiment_prefix="issue-resolver-local",
    )
    rows: list[Any] = list(results)
    tests_scores = [row["evaluation_results"]["results"][0]["score"] for row in rows]
    similarity_scores = [row["evaluation_results"]["results"][1]["score"] for row in rows]
    return {
        "mode": "langsmith",
        "cases": len(rows),
        "tests_pass_rate": round(sum(tests_scores) / len(tests_scores), 3),
        "patch_similarity_avg": round(sum(similarity_scores) / len(similarity_scores), 3),
    }


def main() -> None:
    examples = _load_dataset()
    upload = os.environ.get("LANGSMITH_EVAL_UPLOAD", "").lower() == "true"
    summary = _run_langsmith_eval(examples) if upload else _run_local_eval(examples)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
