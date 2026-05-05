from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langsmith import evaluate

from resolver.graph import build_graph


def _load_dataset() -> list[dict[str, Any]]:
    dataset = Path("evals/dataset.jsonl")
    return [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]


def target(inputs: dict[str, Any]) -> dict[str, Any]:
    graph = build_graph()
    state = graph.invoke(
        {
            "issue": {
                "repo": inputs["repo"],
                "number": int(inputs["issue_number"]),
                "title": inputs.get("title", f"Issue {inputs['issue_number']}"),
                "body": inputs.get("body", ""),
                "local_path": inputs.get("local_path", "."),
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


def main() -> None:
    examples = _load_dataset()
    evaluate(
        target,
        data=examples,
        evaluators=[tests_pass, patch_similarity],
        experiment_prefix="issue-resolver-local",
    )


if __name__ == "__main__":
    main()
