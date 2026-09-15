"""CUSTOM (G-Eval): is every factual claim cited, and do citations hold up?

Uncited claims are the entry point for hallucination — this catches them
even when the claim happens to be correct."""

import pytest

from metrics import qa_metrics
from tests._helpers import run_metric

METRIC_LABEL = "Citation Discipline"


@pytest.mark.custom
@pytest.mark.generation
def test_citation_discipline(test_case):
    run_metric(
        test_case=test_case,
        metric=qa_metrics.citation_discipline(),
        metric_label=METRIC_LABEL,
        category="G-Eval",
        description="Is every factual claim cited, and do the citations hold up?",
    )
