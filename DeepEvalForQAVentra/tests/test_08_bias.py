"""Does the system stay neutral when baited with a loaded prompt?

INVERTED metric — higher score means more bias."""

import pytest

from framework import metrics_registry
from tests._helpers import run_metric

METRIC_LABEL = "Bias"


@pytest.mark.safety
def test_bias(test_case):
    run_metric(
        test_case=test_case,
        metric=metrics_registry.bias(),
        metric_label=METRIC_LABEL,
        category="Safety",
        description="Does the system stay neutral when baited with a loaded prompt?",
       
    )
