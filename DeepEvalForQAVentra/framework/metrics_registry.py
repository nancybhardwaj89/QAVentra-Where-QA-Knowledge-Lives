"""Builds DeepEval's built-in metrics with framework-wide config applied.

Test files call these instead of instantiating metrics directly, so the
judge model and thresholds stay consistent everywhere and can be changed
in one place rather than across 14 files.
"""

from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    HallucinationMetric,
    ToxicityMetric,
    BiasMetric,
    PIILeakageMetric,
)

from framework import config
from framework.judges import get_judge


def _build(metric_cls, name: str, **kwargs):
    """Shared construction — every metric gets the same judge and its
    configured threshold, so no test file has to remember either."""
    return metric_cls(
        threshold=config.threshold_for(name),
        model=get_judge(),
        **kwargs,
    )


# --- RAG quality ---

def answer_relevancy():
    return _build(AnswerRelevancyMetric, "AnswerRelevancy")


def faithfulness():
    return _build(FaithfulnessMetric, "Faithfulness")


def contextual_precision():
    return _build(ContextualPrecisionMetric, "ContextualPrecision")


def contextual_recall():
    return _build(ContextualRecallMetric, "ContextualRecall")


def contextual_relevancy():
    return _build(ContextualRelevancyMetric, "ContextualRelevancy")


# --- Safety (inverted metrics — lower scores are better) ---

def hallucination():
    return _build(HallucinationMetric, "Hallucination")


def toxicity():
    return _build(ToxicityMetric, "Toxicity")


def bias():
    return _build(BiasMetric, "Bias")


def pii_leakage():
    return _build(PIILeakageMetric, "PIILeakage")