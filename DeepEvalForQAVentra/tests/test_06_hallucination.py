"""Does the answer contradict or invent facts against ground truth?

INVERTED metric — a higher score means MORE hallucination, so the
threshold is set low (0.3) in framework/config.py.

Grades against `context` (ground truth) rather than `retrieval_context`
(what the system fetched) — that is what distinguishes it from Faithfulness."""

import pytest

from framework import metrics_registry
from tests._helpers import run_metric

METRIC_LABEL = "Hallucination"


@pytest.mark.safety
@pytest.mark.generation
def test_hallucination(test_case):
    run_metric(
        test_case=test_case,
        metric=metrics_registry.hallucination(),
        metric_label=METRIC_LABEL,
        category="Safety",
        description="Does the answer contradict or invent facts against ground truth?",
        
    )
