"""Shared helper for metric test files.

Every metric test does the same three things — measure, record, assert.
That shared shape lives here so each test file stays a few lines.
"""

import time

from framework import reporting


def run_metric(
    test_case,
    metric,
    metric_label: str,
    category: str = "",
    description: str = "",
    inverted: bool = False,
):
    """Measures one metric against one test case, records it, then asserts.

    We call metric.measure() directly rather than deepeval's assert_test().
    assert_test runs metrics through DeepEval's own internal evaluation
    loop, which does NOT populate score/success/reason back onto the metric
    object we hold — so the dashboard would record nothing but None values.

    Measuring explicitly gives us the populated metric; the assert at the
    end preserves standard pytest pass/fail behaviour either way.

    Args:
        category: grouping shown in the dashboard filter pills
            ("Quality", "Retrieval", "Safety", "G-Eval")
        description: the plain-English question this metric answers,
            shown on its dashboard card
        inverted: True for metrics where a HIGHER score is WORSE
    """
    start = time.time()

    try:
        metric.measure(test_case)
    finally:
        elapsed_ms = int((time.time() - start) * 1000)
        # Record whatever we have, even if measuring raised — a failing run
        # should still produce a complete report.
        reporting.record_single(
            metric_name=metric_label,
            test_case=test_case,
            metric=metric,
            category=category,
            description=description,
            inverted=inverted,
            elapsed_ms=elapsed_ms,
        )

    if not metric.success:
        score = metric.score if metric.score is not None else float("nan")
        raise AssertionError(
            f"{metric_label} scored {score:.3f}, "
            f"threshold {metric.threshold}.\n"
            f"Reason: {metric.reason}"
        )
