"""Are the retrieved chunks relevant to the question at all?

A low score indicates retrieval is pulling in noise alongside signal."""

import pytest

from framework import metrics_registry
from tests._helpers import run_metric

METRIC_LABEL = "Contextual Relevancy"


@pytest.mark.quality
@pytest.mark.retrieval
def test_contextual_relevancy(test_case):
    run_metric(
        test_case=test_case,
        metric=metrics_registry.contextual_relevancy(),
        metric_label=METRIC_LABEL,
        category="Retrieval",
        description="Are the retrieved chunks relevant to the question at all?",
    )
