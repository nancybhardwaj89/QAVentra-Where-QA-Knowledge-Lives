"""Live evaluation dashboard server.

Serves the dashboard at http://localhost:8203 and exposes endpoints that
run metrics on demand — so the Run button on each card actually executes
that metric against the live QAVentra API rather than replaying a stored
result.

Run it:
    python dashboard_server.py

The static build (python build_dashboard.py) still works and produces a
shareable single file; this server is for interactive use, where you want
to re-run a metric after changing a prompt and see the score move.
"""

import json
import os
import time

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from framework import catalog, config
from framework.dataset import build_test_case, get_meta
from framework.judges import get_judge

TEMPLATE_FILE = "dashboard_template.html"
RESULTS_FILE = os.path.join(config.RESULTS_DIR, "results.json")
PORT = int(os.getenv("DASHBOARD_PORT", "8203"))

app = FastAPI(title="QAVentra Evaluation Dashboard")


# ----------------------------------------------------------------------
# Results file helpers
# ----------------------------------------------------------------------

def load_results() -> dict:
    """Reads the stored results, or returns an empty shell if none exist."""
    if not os.path.exists(RESULTS_FILE):
        return {
            "generated_at": None,
            "judge_model": None,
            "target": "QAVentraTarget",
            "target_api": config.TARGET_API_URL,
            "metrics": [],
            "totals": {"metrics": 0, "evaluations": 0, "passed": 0, "failed": 0, "errored": 0},
        }
    with open(RESULTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_results(data: dict) -> None:
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def recount(data: dict) -> dict:
    """Recomputes the top-level tallies after a metric changes."""
    cases = [c for m in data["metrics"] for c in m.get("cases", [])]
    data["totals"] = {
        "metrics": len(data["metrics"]),
        "evaluations": len(cases),
        "passed": sum(1 for c in cases if c.get("success") is True),
        "failed": sum(1 for c in cases if c.get("success") is False),
        "errored": sum(1 for c in cases if c.get("success") is None),
    }
    return data


def skeleton_for(label: str) -> dict:
    """A not-yet-run card, so every catalog metric appears on the dashboard
    even before its first run."""
    entry = catalog.get(label)
    cases = catalog.cases_for(label)
    return {
        "name": label,
        "category": entry["category"],
        "description": entry["description"],
        "inverted": False,
        "threshold": config.threshold_for(label),
        "cases": [],
        "score": None,
        "passed": 0,
        "total": 0,
        "success": None,
        "judge_latency_ms": 0,
        "not_run": True,
        "available_cases": len(cases),
    }


def merge_skeletons(data: dict) -> dict:
    """Adds placeholder cards for catalog metrics that have no results yet."""
    present = {m["name"] for m in data.get("metrics", [])}
    ordered = []
    for label in catalog.all_metrics():
        existing = next((m for m in data["metrics"] if m["name"] == label), None)
        ordered.append(existing if existing else skeleton_for(label))
    # keep any metric in results that isn't in the catalog (renamed, removed)
    for m in data.get("metrics", []):
        if m["name"] not in catalog.CATALOG:
            ordered.append(m)
    data["metrics"] = ordered
    return data


# ----------------------------------------------------------------------
# Running a metric
# ----------------------------------------------------------------------

def run_metric(label: str) -> dict:
    """Runs one metric against its dataset cases and returns a result block."""
    entry = catalog.get(label)
    cases = catalog.cases_for(label)

    if not cases:
        raise HTTPException(
            status_code=400,
            detail=f"No dataset cases declare metric '{label}'.",
        )

    metric = entry["builder"]()
    results = []

    for case in cases:
        test_case = build_test_case(case)
        meta = get_meta(test_case.input)

        start = time.time()
        try:
            metric.measure(test_case)
            score = metric.score
            success = metric.success
            reason = metric.reason
        except Exception as e:
            score, success, reason = None, None, f"Evaluation error: {e}"
        judge_ms = int((time.time() - start) * 1000)

        results.append({
            "case_id": meta.get("id", ""),
            "purpose": meta.get("purpose", ""),
            "question": test_case.input,
            "answer": test_case.actual_output,
            "expected": test_case.expected_output or "",
            "score": score,
            "success": success,
            "reason": reason,
            "context_chunks": meta.get("context_chunks", 0),
            "target_latency_ms": meta.get("latency_ms", 0),
            "judge_latency_ms": judge_ms,
        })

    scored = [r["score"] for r in results if isinstance(r["score"], (int, float))]
    passed = sum(1 for r in results if r["success"])

    return {
        "name": label,
        "category": entry["category"],
        "description": entry["description"],
        "inverted": False,
        "threshold": config.threshold_for(label),
        "cases": results,
        "score": sum(scored) / len(scored) if scored else None,
        "passed": passed,
        "total": len(results),
        "success": passed == len(results) and len(results) > 0,
        "judge_latency_ms": sum(r["judge_latency_ms"] for r in results),
        "not_run": False,
    }


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    if not os.path.exists(TEMPLATE_FILE):
        return HTMLResponse(
            f"<h1>Template not found</h1><p>Expected {TEMPLATE_FILE}</p>",
            status_code=500,
        )
    with open(TEMPLATE_FILE, encoding="utf-8") as f:
        template = f.read()
    # null tells the page to fetch live data instead of using embedded results
    return template.replace("__DASHBOARD_DATA__", "null")


@app.get("/api/results")
def api_results():
    data = merge_skeletons(load_results())
    data["target_api"] = config.TARGET_API_URL
    if not data.get("judge_model"):
        try:
            data["judge_model"] = get_judge().get_model_name()
        except Exception:
            data["judge_model"] = "unknown"
    return recount(data)


@app.post("/api/run/{metric_label}")
def api_run(metric_label: str):
    try:
        block = run_metric(metric_label)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    data = load_results()
    data["metrics"] = [m for m in data.get("metrics", []) if m["name"] != metric_label]
    data["metrics"].append(block)
    data["generated_at"] = __import__("datetime").datetime.now().isoformat()
    try:
        data["judge_model"] = get_judge().get_model_name()
    except Exception:
        pass
    data["target"] = "QAVentraTarget"
    data["target_api"] = config.TARGET_API_URL

    save_results(recount(data))
    return JSONResponse(block)


@app.post("/api/run-all")
def api_run_all():
    """Runs every metric in the catalog. Slow — mainly useful from the UI's
    'Run all' button when you want a fresh full sweep."""
    data = load_results()
    data["metrics"] = []

    for label in catalog.all_metrics():
        try:
            data["metrics"].append(run_metric(label))
        except Exception as e:
            print(f"  [error] {label}: {e}")

    data["generated_at"] = __import__("datetime").datetime.now().isoformat()
    try:
        data["judge_model"] = get_judge().get_model_name()
    except Exception:
        pass
    data["target"] = "QAVentraTarget"
    data["target_api"] = config.TARGET_API_URL

    save_results(recount(data))
    return JSONResponse(data)


if __name__ == "__main__":
    print("=" * 60)
    print(f"QAVentra Evaluation Dashboard")
    print(f"  Dashboard : http://localhost:{PORT}")
    print(f"  Target    : {config.TARGET_API_URL}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=PORT)