import os
import sys
import math
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from groq import Groq
from sentence_transformers import CrossEncoder
from qdrant_client import models

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ingestion"))
from common import get_model, get_client, COLLECTION_NAME  # type: ignore


load_dotenv()

app = FastAPI(title="QAVentra")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)

GROQ_MODEL = "openai/gpt-oss-120b"


# ============================================================
# METADATA-AWARE RETRIEVAL
# Pure semantic similarity treats "bug", "test case", and
# "requirement" as just more words to embed — it has no concept
# that these point to different artifact types with different
# reliability for different question types. This layer nudges
# reranked results toward the artifact type(s) the question is
# actually asking about, without hard-excluding everything else
# (so genuinely relevant cross-source context can still surface).
# ============================================================

QUERY_TYPE_KEYWORDS = {
    ("jira_ticket", "jira_comment"): [
        "bug", "bugs", "defect", "defects", "issue", "issues", "ticket", "tickets", "jira"
    ],
    ("test_case",): [
        "test case", "test cases", "test coverage", "coverage", "scenario", "scenarios"
    ],
    ("document",): [
        "prd", "requirement", "requirements", "acceptance criteria", "srs", "brd", "frd", "spec", "policy"
    ],
    ("code",): [
        "script", "scripts", "automation", "code", "function", "method", "page object", "selector"
    ],
    ("meeting_notes",): [
        "meeting", "discussed", "transcript", "notes"
    ],
}

BOOST_MULTIPLIER = 1.25  # how much to favor matching source types after reranking


def classify_query_boost_types(question: str) -> set:
    """Scans the question for trigger keywords and returns the set of
    source_type values that should get a relevance boost."""
    q_lower = question.lower()
    boosted_types = set()

    for source_types, keywords in QUERY_TYPE_KEYWORDS.items():
        if any(keyword in q_lower for keyword in keywords):
            boosted_types.update(source_types)

    return boosted_types


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


class AskRequest(BaseModel):
    question: str
    filter: str = "all"   # "all" | "jira" | "playwright" | "prd"


def build_source_filter(filter_key: str):
    if filter_key == "jira":
        return models.Filter(
            should=[
                models.FieldCondition(key="source_type", match=models.MatchValue(value="jira_ticket")),
                models.FieldCondition(key="source_type", match=models.MatchValue(value="jira_comment")),
            ]
        )
    elif filter_key == "playwright":
        return models.Filter(
            must=[
                models.FieldCondition(key="source_type", match=models.MatchValue(value="code")),
                models.FieldCondition(key="repo", match=models.MatchValue(value="playwright_framework")),
            ]
        )
    elif filter_key == "prd":
        return models.Filter(
            must=[
                models.FieldCondition(key="source_type", match=models.MatchValue(value="document")),
                models.FieldCondition(key="doc_category", match=models.MatchValue(value="prd_srs_brd_frd")),
            ]
        )
    return None


def hybrid_search_and_rerank(question: str, filter_key: str = "all", top_k: int = 6, candidates: int = 25):
    embed_model = get_model()
    client = get_client()
    qdrant_filter = build_source_filter(filter_key)

    q_output = embed_model.encode([question], return_dense=True, return_sparse=True)
    q_dense = q_output["dense_vecs"][0]
    q_sparse = q_output["lexical_weights"][0]

    prefetch_dense = models.Prefetch(query=q_dense.tolist(), using="dense", limit=candidates)
    prefetch_sparse = models.Prefetch(
        query=models.SparseVector(
            indices=[int(k) for k in q_sparse.keys()],
            values=[float(v) for v in q_sparse.values()]
        ),
        using="sparse",
        limit=candidates
    )
    if qdrant_filter:
        prefetch_dense.filter = qdrant_filter
        prefetch_sparse.filter = qdrant_filter

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[prefetch_dense, prefetch_sparse],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=candidates
    ).points

    if not results:
        return []

    pairs = [(question, r.payload["text"]) for r in results]
    raw_scores = reranker.predict(pairs)

    # Normalize raw cross-encoder logits into a 0-1 range so boosting behaves
    # predictably regardless of the reranker's raw score scale.
    normalized_scores = [sigmoid(float(s)) for s in raw_scores]

    boosted_types = classify_query_boost_types(question)

    adjusted = []
    for r, norm_score in zip(results, normalized_scores):
        source_type = r.payload.get("source_type", "")
        if source_type in boosted_types:
            final_score = min(norm_score * BOOST_MULTIPLIER, 1.0)
        else:
            final_score = norm_score
        adjusted.append((r, final_score))

    reranked = sorted(adjusted, key=lambda x: x[1], reverse=True)

    return reranked[:top_k]


def build_citation_label(payload: dict) -> str:
    source_type = payload.get("source_type", "unknown")
    if source_type == "test_case":
        return f"Test Case {payload.get('test_case_id')}"
    elif source_type == "code":
        return f"Code: {payload.get('file_path')}"
    elif source_type in ("jira_ticket", "jira_comment"):
        return f"JIRA {payload.get('ticket_id')}"
    elif source_type == "meeting_notes":
        return f"Meeting Notes: {payload.get('file_path')}"
    elif source_type == "document":
        return f"Doc: {payload.get('file_path')}"
    return f"Source: {payload.get('file_path', 'unknown')}"


def generate_answer(question: str, ranked_results):
    context_blocks = []
    sources = []

    for i, (r, score) in enumerate(ranked_results, start=1):
        label = build_citation_label(r.payload)
        context_blocks.append(f"[{i}] {label}\n{r.payload['text']}")
        sources.append({"index": i, "label": label, "score": round(float(score), 4)})

    context_text = "\n\n---\n\n".join(context_blocks)

    system_prompt = (
        "You are QAVentra, a QA knowledge assistant. Answer the question ONLY using the "
        "provided context blocks below. Every factual claim in your answer must include a "
        "citation like [1], [2] referring to the context block it came from. "
        "If the context does not contain enough information to answer, say so clearly instead "
        "of guessing or using outside knowledge. If the question asks specifically about one "
        "artifact type (e.g. a reported bug) and the context only contains related-but-different "
        "artifact types (e.g. test cases or code, not an actual bug report), state plainly that "
        "no matching artifact of the requested type was found, before mentioning any related context."
    )

    user_prompt = f"Context:\n\n{context_text}\n\nQuestion: {question}"

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content, sources


@app.post("/ask")
def ask(request: AskRequest):
    ranked_results = hybrid_search_and_rerank(request.question, filter_key=request.filter)

    if not ranked_results:
        return {"answer": "No relevant information found in the knowledge base for this filter.", "sources": []}

    answer, sources = generate_answer(request.question, ranked_results)
    return {"answer": answer, "sources": sources}


@app.get("/stats")
def stats():
    client = get_client()
    count_result = client.count(collection_name=COLLECTION_NAME, exact=True)
    return {"points": count_result.count}


@app.get("/", response_class=HTMLResponse)
def home():
    with open(os.path.join(os.path.dirname(__file__), "..", "ui", "index.html")) as f:
        return f.read()