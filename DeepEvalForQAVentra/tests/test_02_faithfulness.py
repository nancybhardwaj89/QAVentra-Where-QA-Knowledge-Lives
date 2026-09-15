"""Is every claim in the answer grounded in the retrieved context?

This is the core anti-hallucination metric for RAG."""

import pytest

from framework import metrics_registry
from tests._helpers import run_metric

METRIC_LABEL = "Faithfulness"


@pytest.mark.quality
@pytest.mark.generation
def test_faithfulness(test_case):
    run_metric(
        test_case=test_case,
        metric=metrics_registry.faithfulness(),
        metric_label=METRIC_LABEL,
        category="Quality",
        description="Is every claim in the answer grounded in the retrieved context?",
    )
