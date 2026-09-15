"""Collects metric results across test files and writes them to JSON.

pytest runs every test file in one session, so a module-level collector
accumulates results from all metrics, then writes one combined file at
the end of the session (triggered from tests/conftest.py).
"""

import json
import os
import time
from datetime import datetime
from typing import List

from framework import config
from framework.dataset import get_meta

_collected = []


def record_single(
    metric_name: str,
    test_case,
    metric,
    category: str = "",
    description: str = "",
    inverted: bool = False,
    elapsed_ms: int = 0,
) -> None:
    """Records one metric's score for one test case.

    Uses getattr with None defaults because a metric that errored may not
    have all fields populated — better to record a partial result than to
    crash the whole run at the reporting step.
    """
   
    meta = get_meta(test_case.input)

    _collected.append({
        "metric": metric_name,
        "category": category,
        "description": description,
        "inverted": inverted,
        "case_id": meta.get("id", ""),
        "purpose": meta.get("purpose", ""),
        "question": test_case.input,
        "answer": test_case.actual_output,
        "expected": getattr(test_case, "expected_output", ""),
        "context_chunks": meta.get("context_chunks", 0),
        "target_latency_ms": meta.get("latency_ms", 0),
        "judge_latency_ms": elapsed_ms,
        "score": getattr(metric, "score", None),
        "threshold": getattr(metric, "threshold", None),
        "success": getattr(metric, "success", None),
        "reason": getattr(metric, "reason", None),
    })


def _group_by_metric(records: List[dict]) -> List[dict]:
    """The dashboard is a grid of metric cards, so results group by metric
    with the individual cases nested inside each."""
    grouped = {}

    for r in records:
        name = r["metric"]
        if name not in grouped:
            grouped[name] = {
                "name": name,
                "category": r["category"],
                "description": r["description"],
                "inverted": r["inverted"],
                "threshold": r["threshold"],
                "cases": [],
            }
        grouped[name]["cases"].append({
            "case_id": r["case_id"],
            "purpose": r["purpose"],
            "question": r["question"],
            "answer": r["answer"],
            "expected": r["expected"],
            "score": r["score"],
            "success": r["success"],
            "reason": r["reason"],
            "context_chunks": r["context_chunks"],
            "target_latency_ms": r["target_latency_ms"],
            "judge_latency_ms": r["judge_latency_ms"],
        })

    for g in grouped.values():
        scored = [c["score"] for c in g["cases"] if isinstance(c["score"], (int, float))]
        g["score"] = sum(scored) / len(scored) if scored else None
        g["passed"] = sum(1 for c in g["cases"] if c["success"])
        g["total"] = len(g["cases"])
        g["success"] = g["passed"] == g["total"] and g["total"] > 0
        g["judge_latency_ms"] = sum(c["judge_latency_ms"] for c in g["cases"])

    return list(grouped.values())


def write_results(judge_name: str = "unknown", target_name: str = "unknown") -> str:
    """Writes collected results to JSON. Returns the file path."""
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    path = os.path.join(config.RESULTS_DIR, "results.json")

    metrics = _group_by_metric(_collected)

    output = {
        "generated_at": datetime.now().isoformat(),
        "judge_model": judge_name,
        "target": target_name,
        "target_api": config.TARGET_API_URL,
        "metrics": metrics,
        "totals": {
            "metrics": len(metrics),
            "evaluations": len(_collected),
            "passed": sum(1 for r in _collected if r["success"]),
            "failed": sum(1 for r in _collected if r["success"] is False),
            "errored": sum(1 for r in _collected if r["success"] is None),
        },
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    return path


def summary_line() -> str:
    """One-line summary printed at the end of a pytest run."""
    if not _collected:
        return "No metric results collected."
    scored = [r for r in _collected if isinstance(r["score"], (int, float))]
    passed = sum(1 for r in _collected if r["success"])
    avg = sum(r["score"] for r in scored) / len(scored) if scored else 0
    return (
        f"{len(_collected)} metric evaluations · "
        f"{passed} passed · avg score {avg:.3f}"
    )
