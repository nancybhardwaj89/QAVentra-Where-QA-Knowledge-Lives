"""CUSTOM (G-Eval): does it stay inside the knowledge base?

General software-testing knowledge — even when factually correct — breaks
the core promise that answers come from the team's own artifacts."""

import pytest

from metrics import qa_metrics
from tests._helpers import run_metric

METRIC_LABEL = "Scope Adherence"


@pytest.mark.custom
@pytest.mark.generation
def test_scope_adherence(test_case):
    run_metric(
        test_case=test_case,
        metric=qa_metrics.scope_adherence(),
        metric_label=METRIC_LABEL,
        category="G-Eval",
        description="Does it stay inside the knowledge base, or add outside knowledge?",
    )
