"""Single source of truth for every metric in the suite.

Both pytest and the dashboard server read from here, so a metric's
category, description and threshold are defined once rather than
duplicated across a test file and a server route.

Each entry maps a metric label to:
    builder     — callable returning a fresh metric instance
    category    — dashboard grouping / filter pill
    description — the plain-English question the metric answers
    cases       — dataset case ids this metric runs against
"""

from framework import metrics_registry
from datasets.qaventra_dataset import DATASET


CATALOG = {
    # ---------------- RAG quality ----------------
    "Answer Relevancy": {
        "builder": metrics_registry.answer_relevancy,
        "category": "Quality",
        "description": "Does the answer address the question that was actually asked?",
    },
    "Faithfulness": {
        "builder": metrics_registry.faithfulness,
        "category": "Quality",
        "description": "Is every claim in the answer grounded in the retrieved context?",
    },

    # ---------------- Retrieval ----------------
    "Contextual Precision": {
        "builder": metrics_registry.contextual_precision,
        "category": "Retrieval",
        "description": "Are the retrieved chunks ranked with the relevant ones on top?",
    },
    "Contextual Recall": {
        "builder": metrics_registry.contextual_recall,
        "category": "Retrieval",
        "description": "Did retrieval find everything the reference answer needs?",
    },
    "Contextual Relevancy": {
        "builder": metrics_registry.contextual_relevancy,
        "category": "Retrieval",
        "description": "Are the retrieved chunks relevant to the question at all?",
    },

    # ---------------- Safety ----------------
    "Hallucination": {
        "builder": metrics_registry.hallucination,
        "category": "Safety",
        "description": "Does the answer contradict or invent facts against ground truth?",
    },
    "Toxicity": {
        "builder": metrics_registry.toxicity,
        "category": "Safety",
        "description": "Is the reply free of insults, mockery and demeaning language?",
    },
    "Bias": {
        "builder": metrics_registry.bias,
        "category": "Safety",
        "description": "Does the system stay neutral when baited with a loaded prompt?",
    },
    "PII Leakage": {
        "builder": metrics_registry.pii_leakage,
        "category": "Safety",
        "description": "Does the reply leak personal data or hidden system context?",
    },
}


def _register_custom():
    """Custom G-Eval metrics are imported lazily so the catalog can be
    imported without pulling in the judge when it isn't needed."""
    from metrics import qa_metrics

    CATALOG.update({
        "Artifact Type Precision": {
            "builder": qa_metrics.artifact_type_precision,
            "category": "G-Eval",
            "description": "Does the answer respect QA artifact type boundaries?",
        },
        "Citation Discipline": {
            "builder": qa_metrics.citation_discipline,
            "category": "G-Eval",
            "description": "Is every factual claim cited, and do the citations hold up?",
        },
        "Honest Absence Handling": {
            "builder": qa_metrics.honest_absence,
            "category": "G-Eval",
            "description": "Does it say 'not found' plainly instead of hedging?",
        },
        "QA Actionability": {
            "builder": qa_metrics.qa_actionability,
            "category": "G-Eval",
            "description": "Could a QA engineer act on this without searching again?",
        },
        "Scope Adherence": {
            "builder": qa_metrics.scope_adherence,
            "category": "G-Eval",
            "description": "Does it stay inside the knowledge base, or add outside knowledge?",
        },
    })


_register_custom()


def get(metric_label: str) -> dict:
    """Returns the catalog entry for a metric, or raises with a clear message."""
    if metric_label not in CATALOG:
        raise KeyError(
            f"Unknown metric '{metric_label}'. "
            f"Known metrics: {', '.join(sorted(CATALOG))}"
        )
    return CATALOG[metric_label]


def cases_for(metric_label: str) -> list:
    """Returns the dataset entries that declare this metric."""
    selected = []
    for case in DATASET:
        applies = case.get("metrics", "*")
        if applies == "*" or metric_label in applies:
            selected.append(case)
    return selected


def all_metrics() -> list:
    """Every metric label, in catalog order."""
    return list(CATALOG.keys())