"""Custom G-Eval metrics specific to a QA knowledge system.

Built-in metrics measure generic RAG quality. These measure domain
behaviour — including the artifact-type confusion found during manual
testing, where a question about bugs surfaced test cases instead.

G-Eval uses an LLM judge scoring against plain-English criteria, so these
read like a QA review rubric rather than code.

Each criteria block includes explicit "do NOT penalise" clauses. This
matters a lot: vague criteria produce noisy, inconsistent scores, so
telling the judge what shouldn't count is as important as what should.
"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

from framework import config
from framework.judges import get_judge


def _geval(name: str, criteria: str, params: list) -> GEval:
    """Shared construction — same pattern as metrics_registry, so custom
    metrics get the same judge and threshold handling as built-ins."""
    return GEval(
        name=name,
        criteria=criteria,
        evaluation_params=params,
        threshold=config.threshold_for(name),
        model=get_judge(),
    )


def artifact_type_precision() -> GEval:
    """Catches bug questions being answered with test cases."""
    return _geval(
        "Artifact Type Precision",
        (
            "Determine whether the output correctly distinguishes between different "
            "QA artifact types — bugs/defects, test cases, requirements/PRDs, and "
            "automation code — and answers using the type the question actually asked about. "
            "If the question asks about a BUG, the answer should be about reported defects, "
            "not test cases that merely test similar functionality. "
            "If the question asks about TEST CASES, the answer should not substitute "
            "requirements or code. "
            "If the correct artifact type does not exist in the context, the answer should "
            "say so explicitly rather than substituting a different artifact type as if it "
            "were equivalent. "
            "Mentioning related artifacts as clearly-labelled additional context is "
            "acceptable and should NOT be penalised — substituting them for the "
            "requested type should be."
        ),
        [
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT,
        ],
    )


def citation_discipline() -> GEval:
    """Uncited claims are where hallucination enters."""
    return _geval(
        "Citation Discipline",
        (
            "Determine whether every factual claim in the output carries a citation "
            "marker (such as [1], [2]) and whether those citations correspond to "
            "information actually present in the retrieval context. "
            "Penalise factual claims stated without any citation. "
            "Penalise citations attached to claims the cited context does not support. "
            "General framing sentences, transitions, and statements that no information "
            "was found do NOT require citations and should not be penalised."
        ),
        [
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT,
        ],
    )


def honest_absence() -> GEval:
    """Scores the 'says not found instead of hedging' behaviour."""
    return _geval(
        "Honest Absence Handling",
        (
            "Determine whether the output is appropriately direct when the retrieval "
            "context does not contain an answer to the question. "
            "If the context genuinely lacks the requested information, a high score "
            "requires the output to state plainly and early that it was not found. "
            "Penalise vague hedging, burying the absence at the end of a long answer, "
            "or implying an answer exists when it does not. "
            "If the context DOES contain the answer, this criterion is satisfied by the "
            "output simply answering the question — do NOT penalise it for the absence "
            "of a 'not found' statement."
        ),
        [
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT,
        ],
    )


def qa_actionability() -> GEval:
    """An answer a QA engineer can't act on isn't useful."""
    return _geval(
        "QA Actionability",
        (
            "Determine whether a QA engineer could act on this output without having "
            "to go searching elsewhere first. "
            "High-scoring answers include the concrete identifiers present in the "
            "context — ticket keys, test case IDs, file paths, module or sub-module "
            "names — rather than describing artifacts only in general terms. "
            "Penalise answers that say relevant items exist but do not name them when "
            "the context provides the names. "
            "Do NOT penalise an answer for omitting identifiers that are genuinely "
            "absent from the context."
        ),
        [
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT,
        ],
    )


def scope_adherence() -> GEval:
    """General knowledge, even when correct, breaks the grounding promise."""
    return _geval(
        "Scope Adherence",
        (
            "Determine whether the output stays strictly within the provided retrieval "
            "context and does not introduce general software-testing knowledge, industry "
            "best practices, or outside facts not present in the context. "
            "Penalise plausible-sounding additions the context does not support, even if "
            "they are factually correct in general. "
            "The system's promise is that answers come from the team's own knowledge base, "
            "so unsupported general knowledge is a failure even when accurate."
            "Statements that the context does NOT contain something, or that the "
            "knowledge base lacks certain information, are meta-observations about "
            "the context rather than outside knowledge — do NOT penalise them."
        ),
        [
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT,
        ],
    )