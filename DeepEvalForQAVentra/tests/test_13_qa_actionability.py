"""CUSTOM (G-Eval): could a QA engineer act on this without searching again?

Measures whether answers name concrete identifiers (ticket keys, test case
IDs, file paths) rather than vaguely describing what exists."""

import pytest

from metrics import qa_metrics
from tests._helpers import run_metric

METRIC_LABEL = "QA Actionability"


@pytest.mark.custom
@pytest.mark.generation
def test_qa_actionability(test_case):
    run_metric(
        test_case=test_case,
        metric=qa_metrics.qa_actionability(),
        metric_label=METRIC_LABEL,
        category="G-Eval",
        description="Could a QA engineer act on this without searching again?",
    )
