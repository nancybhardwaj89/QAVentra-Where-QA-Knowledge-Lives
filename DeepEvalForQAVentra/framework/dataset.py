"""Dataset loading and conversion into DeepEval test cases.

Datasets are plain dicts (see datasets/) so they stay readable and
reviewable by people who don't write Python — which matters when the
ground truth needs sign-off from whoever owns the domain knowledge.
"""

import time
from typing import List

from deepeval.test_case import LLMTestCase

from framework import config
from framework.target import get_target


REQUIRED_KEYS = {"question", "expected_answer"}

# LLMTestCase is a Pydantic model and rejects arbitrary attributes, so the
# extra metadata the dashboard shows (case id, purpose, timings) lives here
# instead, keyed by question.
_CASE_META = {}


def get_meta(question: str) -> dict:
    """Returns the dashboard metadata recorded for a question."""
    return _CASE_META.get(question, {})


def validate_case(case: dict, index: int = 0) -> None:
    """Fails fast on a malformed case rather than deep inside a metric."""
    missing = REQUIRED_KEYS - case.keys()
    if missing:
        label = case.get("id", f"case {index}")
        raise ValueError(f"Dataset {label} is missing required key(s): {sorted(missing)}")


def build_test_case(case: dict) -> LLMTestCase:
    """Queries the live system for one dataset entry and wraps the result
    as a DeepEval test case."""
    validate_case(case)

    target = get_target()
    start = time.time()

    response = target.query(
        case["question"],
        source_filter=case.get("filter", "all"),
    )

    elapsed_ms = int((time.time() - start) * 1000)

    test_case = LLMTestCase(
        input=case["question"],
        actual_output=response.answer,
        expected_output=case["expected_answer"],
        retrieval_context=response.retrieval_context,
        # HallucinationMetric grades against `context` (ground truth),
        # not `retrieval_context` (what the system actually fetched).
        context=[case["expected_answer"]],
    )

    _CASE_META[case["question"]] = {
        "id": case.get("id", case["question"][:45]),
        "purpose": case.get("purpose", ""),
        "latency_ms": elapsed_ms,
        "context_chunks": len(response.retrieval_context),
    }

    if config.DELAY_BETWEEN_CASES:
        time.sleep(config.DELAY_BETWEEN_CASES)

    return test_case


def build_test_cases(dataset: List[dict], verbose: bool = True) -> List[LLMTestCase]:
    """Builds every case in a dataset. Kept for scripts that want the whole
    set at once; pytest uses build_test_case via conftest instead."""
    cases = []
    for i, case in enumerate(dataset, start=1):
        if verbose:
            print(f"  [{i}/{len(dataset)}] {case['question']}")
        cases.append(build_test_case(case))
    return cases