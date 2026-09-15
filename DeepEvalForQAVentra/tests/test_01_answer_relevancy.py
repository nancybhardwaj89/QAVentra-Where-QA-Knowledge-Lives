"""Does the answer address the question that was actually asked?"""

import pytest

from framework import metrics_registry
from tests._helpers import run_metric

METRIC_LABEL = "Answer Relevancy"


@pytest.mark.quality
@pytest.mark.generation
def test_answer_relevancy(test_case):
    run_metric(
        test_case=test_case,
        metric=metrics_registry.answer_relevancy(),
        metric_label=METRIC_LABEL,
        category="Quality",
        description="Does the answer address the question that was actually asked?",
    )
