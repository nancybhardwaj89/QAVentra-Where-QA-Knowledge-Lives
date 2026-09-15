"""Did retrieval find everything the reference answer needs?

A low score means the right chunks were never retrieved at all —
a chunking/embedding problem, not a ranking problem."""

import pytest

from framework import metrics_registry
from tests._helpers import run_metric

METRIC_LABEL = "Contextual Recall"


@pytest.mark.quality
@pytest.mark.retrieval
def test_contextual_recall(test_case):
    run_metric(
        test_case=test_case,
        metric=metrics_registry.contextual_recall(),
        metric_label=METRIC_LABEL,
        category="Retrieval",
        description="Did retrieval find everything the reference answer needs?",
    )
