"""CUSTOM (G-Eval): does it say "not found" plainly instead of hedging?

A QA knowledge system that hedges when it should say "no such bug exists"
wastes the engineer's time verifying."""

import pytest

from metrics import qa_metrics
from tests._helpers import run_metric

METRIC_LABEL = "Honest Absence Handling"


@pytest.mark.custom
@pytest.mark.generation
def test_honest_absence(test_case):
    run_metric(
        test_case=test_case,
        metric=qa_metrics.honest_absence(),
        metric_label=METRIC_LABEL,
        category="G-Eval",
        description="Does it say 'not found' plainly instead of hedging?",
    )
