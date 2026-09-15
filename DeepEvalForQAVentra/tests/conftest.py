"""Shared pytest fixtures and parametrization.

Three things happen here:

1. The live system is queried ONCE per question per session — cached, so
   metrics sharing a question reuse the same response rather than
   re-querying (which would also mean grading different answers).

2. Each metric test only runs against the dataset cases that declare it
   in their `metrics` list. Every metric gets a case chosen to stress it,
   and run time stays proportional to the dataset rather than exploding
   as metrics-by-questions.

3. Results are written once at the end of the session.

A test file opts in by declaring a module-level METRIC_LABEL, which must
match the label used in its run_metric() call.
"""

import sys
from pathlib import Path

import pytest

# Make the framework importable when running pytest from the
# DeepEvalForQAVentra/ root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from framework import reporting
from framework.dataset import build_test_case
from framework.judges import get_judge
from framework.target import get_target
from datasets.qaventra_dataset import DATASET

# question -> LLMTestCase, so two metrics sharing a question hit the API once
_case_cache = {}


def _cases_for_metric(metric_label: str):
    """Returns the dataset entries that apply to this metric."""
    selected = []
    for case in DATASET:
        applies = case.get("metrics", "*")
        if applies == "*" or metric_label in applies:
            selected.append(case)
    return selected


def _build_or_reuse(case: dict):
    """Queries the live system, reusing a cached response per question."""
    key = case["question"]
    if key not in _case_cache:
        print(f"\n  [query] {case['question']}")
        _case_cache[key] = build_test_case(case)
    return _case_cache[key]


def pytest_generate_tests(metafunc):
    """Parametrizes any test declaring a `test_case` argument, scoped to
    the cases relevant to that test's METRIC_LABEL."""
    if "test_case" not in metafunc.fixturenames:
        return

    metric_label = getattr(metafunc.module, "METRIC_LABEL", None)

    if metric_label is None:
        raise RuntimeError(
            f"{metafunc.module.__name__} uses the `test_case` fixture but does "
            "not define METRIC_LABEL. Add it at module level, matching the "
            "label passed to run_metric()."
        )

    cases = _cases_for_metric(metric_label)

    if not cases:
        pytest.skip(
            f"No dataset cases declare metric '{metric_label}'. "
            "Add it to a case's `metrics` list in datasets/qaventra_dataset.py."
        )

    built = [_build_or_reuse(c) for c in cases]
    ids = [c.get("id", c["question"][:45]) for c in cases]

    metafunc.parametrize("test_case", built, ids=ids)


@pytest.fixture(scope="session")
def judge():
    return get_judge()


def pytest_sessionfinish(session, exitstatus):
    """Writes the combined results file after every metric has run."""
    try:
        judge_name = get_judge().get_model_name()
    except Exception:
        judge_name = "unknown"

    try:
        target_name = get_target().name()
    except Exception:
        target_name = "unknown"

    path = reporting.write_results(judge_name=judge_name, target_name=target_name)
    print("\n" + "=" * 60)
    print(reporting.summary_line())
    print(f"Results written to: {path}")
    print("Build the dashboard:  python build_dashboard.py")
    print("=" * 60)
