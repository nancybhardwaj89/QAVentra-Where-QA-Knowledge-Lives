"""Does the reply leak personal data or hidden system context?

Especially relevant here: the knowledge base covers a healthcare domain,
so PHI/PII exposure is a real risk rather than a theoretical one.

INVERTED metric — higher score means more leakage."""

import pytest

from framework import metrics_registry
from tests._helpers import run_metric

METRIC_LABEL = "PII Leakage"


@pytest.mark.safety
def test_pii_leakage(test_case):
    run_metric(
        test_case=test_case,
        metric=metrics_registry.pii_leakage(),
        metric_label=METRIC_LABEL,
        category="Safety",
        description="Does the reply leak personal data or hidden system context?",
        
    )
