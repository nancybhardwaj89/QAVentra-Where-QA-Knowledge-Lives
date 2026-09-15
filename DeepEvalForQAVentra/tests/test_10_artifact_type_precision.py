"""CUSTOM (G-Eval): does the answer respect QA artifact type boundaries?

Written in response to a real failure found during manual testing: asking
"is there a bug related to login?" returned test cases and automation code,
because pure semantic similarity treats "bug", "test case", and
"requirement" as just more words to embed.

This metric turns that qualitative finding into a tracked number."""

import pytest

from metrics import qa_metrics
from tests._helpers import run_metric

METRIC_LABEL = "Artifact Type Precision"


@pytest.mark.custom
@pytest.mark.quality
def test_artifact_type_precision(test_case):
    run_metric(
        test_case=test_case,
        metric=qa_metrics.artifact_type_precision(),
        metric_label=METRIC_LABEL,
        category="G-Eval",
        description="Does the answer respect QA artifact type boundaries?",
    )
