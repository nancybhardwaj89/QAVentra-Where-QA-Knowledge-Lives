"""Are the retrieved chunks ranked with the relevant ones on top?

A low score means the right chunks WERE retrieved but ranked poorly —
a reranking problem, not a retrieval problem."""

import pytest

from framework import metrics_registry
from tests._helpers import run_metric

METRIC_LABEL = "Contextual Precision"


@pytest.mark.quality
@pytest.mark.retrieval
def test_contextual_precision(test_case):
    run_metric(
        test_case=test_case,
        metric=metrics_registry.contextual_precision(),
        metric_label=METRIC_LABEL,
        category="Retrieval",
        description="Are the retrieved chunks ranked with the relevant ones on top?",
    )
