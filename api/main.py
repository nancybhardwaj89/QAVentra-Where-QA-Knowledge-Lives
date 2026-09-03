import os
import sys
import math
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from groq import Groq
from sentence_transformers import CrossEncoder
from qdrant_client import models


# ============================================================
# IMPORT INGESTION / SHARED COMPONENTS
# ============================================================

sys.path.append(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "ingestion"
    )
)

from common import get_model, get_client, COLLECTION_NAME  # type: ignore


# ============================================================
# ENVIRONMENT / APP CONFIG
# ============================================================

load_dotenv()

app = FastAPI(title="QAVentra")

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

reranker = CrossEncoder(
    "BAAI/bge-reranker-v2-m3",
    max_length=512
)

GROQ_MODEL = "openai/gpt-oss-120b"


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def warm_up_models():
    """
    Loads BGE-M3 into memory immediately when the app starts,
    instead of on the first real request.

    This avoids the first caller (a user or MCP client)
    timing out while the model loads cold.
    """

    print(
        "Warming up embedding model on startup...",
        flush=True
    )

    start = time.time()

    get_model()

    elapsed = time.time() - start

    print(
        f"Embedding model ready. Startup load time: {elapsed:.2f}s",
        flush=True
    )


# ============================================================
# METADATA-AWARE RETRIEVAL
# ============================================================

QUERY_TYPE_KEYWORDS = {
    ("jira_ticket", "jira_comment"): [
        "bug",
        "bugs",
        "defect",
        "defects",
        "issue",
        "issues",
        "ticket",
        "tickets",
        "jira",
    ],

    ("test_case",): [
        "test case",
        "test cases",
        "test coverage",
        "coverage",
        "scenario",
        "scenarios",
    ],

    ("document",): [
        "prd",
        "requirement",
        "requirements",
        "acceptance criteria",
        "srs",
        "brd",
        "frd",
        "spec",
        "policy",
    ],

    ("code",): [
        "script",
        "scripts",
        "automation",
        "code",
        "function",
        "method",
        "page object",
        "selector",
    ],

    ("meeting_notes",): [
        "meeting",
        "discussed",
        "transcript",
        "notes",
    ],
}


BOOST_MULTIPLIER = 1.25


# ============================================================
# QUERY CLASSIFICATION
# ============================================================

def classify_query_boost_types(question: str) -> set:
    """
    Scans the question for trigger keywords and returns the set
    of source_type values that should get a relevance boost.
    """

    q_lower = question.lower()

    boosted_types = set()

    for source_types, keywords in QUERY_TYPE_KEYWORDS.items():
        if any(keyword in q_lower for keyword in keywords):
            boosted_types.update(source_types)

    return boosted_types


# ============================================================
# UTILITY
# ============================================================

def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


# ============================================================
# REQUEST MODEL
# ============================================================

class AskRequest(BaseModel):
    question: str
    filter: str = "all"
    # "all" | "jira" | "playwright" | "prd"


# ============================================================
# SOURCE FILTER
# ============================================================

def build_source_filter(filter_key: str):

    if filter_key == "jira":

        return models.Filter(
            should=[
                models.FieldCondition(
                    key="source_type",
                    match=models.MatchValue(
                        value="jira_ticket"
                    ),
                ),

                models.FieldCondition(
                    key="source_type",
                    match=models.MatchValue(
                        value="jira_comment"
                    ),
                ),
            ]
        )

    elif filter_key == "playwright":

        return models.Filter(
            must=[
                models.FieldCondition(
                    key="source_type",
                    match=models.MatchValue(
                        value="code"
                    ),
                ),

                models.FieldCondition(
                    key="repo",
                    match=models.MatchValue(
                        value="playwright_framework"
                    ),
                ),
            ]
        )

    elif filter_key == "prd":

        return models.Filter(
            must=[
                models.FieldCondition(
                    key="source_type",
                    match=models.MatchValue(
                        value="document"
                    ),
                ),

                models.FieldCondition(
                    key="doc_category",
                    match=models.MatchValue(
                        value="prd_srs_brd_frd"
                    ),
                ),
            ]
        )

    return None


# ============================================================
# HYBRID SEARCH + RERANKING
# ============================================================

def hybrid_search_and_rerank(
    question: str,
    filter_key: str = "all",
    top_k: int = 6,
    candidates: int = 25,
):
    """
    Performs:

    1. Query embedding
    2. Qdrant hybrid dense + sparse retrieval
    3. BGE reranking
    4. Metadata-based score boosting

    Detailed timing is logged for every stage so that
    performance bottlenecks can be identified.
    """

    total_start = time.time()

    print(
        "=== RETRIEVAL START ===",
        flush=True
    )

    # --------------------------------------------------------
    # STEP 1: LOAD MODEL / CLIENT
    # --------------------------------------------------------

    start = time.time()

    embed_model = get_model()
    client = get_client()

    qdrant_filter = build_source_filter(
        filter_key
    )

    print(
        f"[TIMING] Model/client initialization: "
        f"{time.time() - start:.2f}s",
        flush=True
    )

    # --------------------------------------------------------
    # STEP 2: QUERY EMBEDDING
    # --------------------------------------------------------

    start = time.time()

    q_output = embed_model.encode(
        [question],
        return_dense=True,
        return_sparse=True
    )

    q_dense = q_output["dense_vecs"][0]
    q_sparse = q_output["lexical_weights"][0]

    print(
        f"[TIMING] Query embedding: "
        f"{time.time() - start:.2f}s",
        flush=True
    )

    # --------------------------------------------------------
    # STEP 3: BUILD QDRANT PREFETCH
    # --------------------------------------------------------

    start = time.time()

    prefetch_dense = models.Prefetch(
        query=q_dense.tolist(),
        using="dense",
        limit=candidates
    )

    prefetch_sparse = models.Prefetch(
        query=models.SparseVector(
            indices=[
                int(k)
                for k in q_sparse.keys()
            ],
            values=[
                float(v)
                for v in q_sparse.values()
            ]
        ),
        using="sparse",
        limit=candidates
    )

    if qdrant_filter:

        prefetch_dense.filter = qdrant_filter
        prefetch_sparse.filter = qdrant_filter

    print(
        f"[TIMING] Qdrant query construction: "
        f"{time.time() - start:.2f}s",
        flush=True
    )

    # --------------------------------------------------------
    # STEP 4: QDRANT HYBRID SEARCH
    # --------------------------------------------------------

    start = time.time()

    results = client.query_points(
        collection_name=COLLECTION_NAME,

        prefetch=[
            prefetch_dense,
            prefetch_sparse
        ],

        query=models.FusionQuery(
            fusion=models.Fusion.RRF
        ),

        limit=candidates
    ).points

    print(
        f"[TIMING] Qdrant hybrid search: "
        f"{time.time() - start:.2f}s",
        flush=True
    )

    print(
        f"[INFO] Qdrant returned "
        f"{len(results)} candidates.",
        flush=True
    )

    if not results:

        print(
            "=== RETRIEVAL END: NO RESULTS ===",
            flush=True
        )

        return []

    # --------------------------------------------------------
    # STEP 5: BUILD RERANKER PAIRS
    # --------------------------------------------------------

    start = time.time()

    pairs = [
        (
            question,
            r.payload["text"]
        )
        for r in results
    ]

    print(
        f"[TIMING] Reranker input preparation: "
        f"{time.time() - start:.2f}s",
        flush=True
    )

    # --------------------------------------------------------
    # STEP 6: BGE RERANKING
    # --------------------------------------------------------

    start = time.time()

    raw_scores = reranker.predict(
        pairs
    )

    reranker_elapsed = time.time() - start

    print(
        f"[TIMING] BGE reranker "
        f"({len(pairs)} candidates): "
        f"{reranker_elapsed:.2f}s",
        flush=True
    )

    # --------------------------------------------------------
    # STEP 7: SCORE NORMALIZATION + BOOSTING
    # --------------------------------------------------------

    start = time.time()

    normalized_scores = [
        sigmoid(float(s))
        for s in raw_scores
    ]

    boosted_types = classify_query_boost_types(
        question
    )

    adjusted = []

    for r, norm_score in zip(
        results,
        normalized_scores
    ):

        source_type = r.payload.get(
            "source_type",
            ""
        )

        if source_type in boosted_types:

            final_score = min(
                norm_score * BOOST_MULTIPLIER,
                1.0
            )

        else:

            final_score = norm_score

        adjusted.append(
            (
                r,
                final_score
            )
        )

    reranked = sorted(
        adjusted,
        key=lambda x: x[1],
        reverse=True
    )

    print(
        f"[TIMING] Score normalization/boosting: "
        f"{time.time() - start:.2f}s",
        flush=True
    )

    # --------------------------------------------------------
    # TOTAL RETRIEVAL TIME
    # --------------------------------------------------------

    total_elapsed = (
        time.time() - total_start
    )

    print(
        f"[TIMING] TOTAL RETRIEVAL: "
        f"{total_elapsed:.2f}s",
        flush=True
    )

    print(
        "=== RETRIEVAL END ===",
        flush=True
    )

    return reranked[:top_k]


# ============================================================
# CITATION LABEL
# ============================================================

def build_citation_label(payload: dict) -> str:

    source_type = payload.get(
        "source_type",
        "unknown"
    )

    if source_type == "test_case":

        return (
            f"Test Case "
            f"{payload.get('test_case_id')}"
        )

    elif source_type == "code":

        return (
            f"Code: "
            f"{payload.get('file_path')}"
        )

    elif source_type in (
        "jira_ticket",
        "jira_comment",
    ):

        return (
            f"JIRA "
            f"{payload.get('ticket_id')}"
        )

    elif source_type == "meeting_notes":

        return (
            f"Meeting Notes: "
            f"{payload.get('file_path')}"
        )

    elif source_type == "document":

        return (
            f"Doc: "
            f"{payload.get('file_path')}"
        )

    return (
        f"Source: "
        f"{payload.get('file_path', 'unknown')}"
    )


# ============================================================
# ANSWER GENERATION
# ============================================================

def generate_answer(
    question: str,
    ranked_results
):
    """
    Generates a grounded answer using only the retrieved
    QAVentra knowledge-base context.
    """

    total_start = time.time()

    print(
        "=== GROQ GENERATION START ===",
        flush=True
    )

    context_blocks = []
    sources = []

    # --------------------------------------------------------
    # STEP 1: BUILD CONTEXT
    # --------------------------------------------------------

    start = time.time()

    for i, (r, score) in enumerate(
        ranked_results,
        start=1
    ):

        label = build_citation_label(
            r.payload
        )

        context_blocks.append(
            f"[{i}] {label}\n"
            f"{r.payload['text']}"
        )

        sources.append(
            {
                "index": i,
                "label": label,
                "score": round(
                    float(score),
                    4
                ),
            }
        )

    context_text = "\n\n---\n\n".join(
        context_blocks
    )

    print(
        f"[TIMING] Context construction: "
        f"{time.time() - start:.2f}s",
        flush=True
    )

    # --------------------------------------------------------
    # STEP 2: SYSTEM PROMPT
    # --------------------------------------------------------

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

    user_prompt = (
        f"Context:\n\n{context_text}\n\n"
        f"Question: {question}"
    )

    print(
        f"[INFO] Context characters: "
        f"{len(context_text)}",
        flush=True
    )

    print(
        f"[INFO] User prompt characters: "
        f"{len(user_prompt)}",
        flush=True
    )

    # --------------------------------------------------------
    # STEP 3: GROQ API CALL
    # --------------------------------------------------------

    start = time.time()

    print(
        f"[INFO] Calling Groq model: "
        f"{GROQ_MODEL}",
        flush=True
    )

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,

        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },

            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        temperature=0.2
    )

    groq_elapsed = time.time() - start

    print(
        f"[TIMING] Groq API generation: "
        f"{groq_elapsed:.2f}s",
        flush=True
    )

    # --------------------------------------------------------
    # STEP 4: RESPONSE EXTRACTION
    # --------------------------------------------------------

    start = time.time()

    answer = response.choices[0].message.content

    print(
        f"[INFO] Answer characters: "
        f"{len(answer) if answer else 0}",
        flush=True
    )

    print(
        f"[TIMING] Response extraction: "
        f"{time.time() - start:.2f}s",
        flush=True
    )

    # --------------------------------------------------------
    # TOTAL GENERATION TIME
    # --------------------------------------------------------

    total_elapsed = (
        time.time() - total_start
    )

    print(
        f"[TIMING] TOTAL ANSWER GENERATION: "
        f"{total_elapsed:.2f}s",
        flush=True
    )

    print(
        "=== GROQ GENERATION END ===",
        flush=True
    )

    return (
        answer,
        sources
    )


# ============================================================
# ASK ENDPOINT
# ============================================================

@app.post("/ask")
def ask(request: AskRequest):

    request_start = time.time()

    print(
        "\n========================================",
        flush=True
    )

    print(
        "=== /ask START ===",
        flush=True
    )

    print(
        f"Question: {request.question}",
        flush=True
    )

    print(
        f"Filter: {request.filter}",
        flush=True
    )

    try:

        # ----------------------------------------------------
        # STEP 1: RETRIEVAL
        # ----------------------------------------------------

        print(
            "1. Starting retrieval...",
            flush=True
        )

        ranked_results = hybrid_search_and_rerank(
            request.question,
            filter_key=request.filter,
        )

        print(
            f"2. Retrieval complete. "
            f"Results: {len(ranked_results)}",
            flush=True
        )

        # ----------------------------------------------------
        # STEP 2: NO RESULTS
        # ----------------------------------------------------

        if not ranked_results:

            print(
                "3. No relevant results found.",
                flush=True
            )

            total_elapsed = (
                time.time() - request_start
            )

            print(
                f"[TIMING] TOTAL /ask: "
                f"{total_elapsed:.2f}s",
                flush=True
            )

            return {
                "answer": (
                    "No relevant information found "
                    "in the knowledge base for this filter."
                ),

                "sources": [],
            }

        # ----------------------------------------------------
        # STEP 3: GENERATE ANSWER
        # ----------------------------------------------------

        print(
            "3. Starting generate_answer...",
            flush=True
        )

        answer, sources = generate_answer(
            request.question,
            ranked_results,
        )

        print(
            "4. generate_answer complete.",
            flush=True
        )

        # ----------------------------------------------------
        # TOTAL REQUEST TIME
        # ----------------------------------------------------

        total_elapsed = (
            time.time() - request_start
        )

        print(
            f"[TIMING] TOTAL /ask: "
            f"{total_elapsed:.2f}s",
            flush=True
        )

        print(
            "=== /ask SUCCESS ===",
            flush=True
        )

        print(
            "========================================\n",
            flush=True
        )

        return {
            "answer": answer,
            "sources": sources,
        }

    except Exception as e:

        # ----------------------------------------------------
        # ERROR DIAGNOSTICS
        # ----------------------------------------------------

        import traceback

        total_elapsed = (
            time.time() - request_start
        )

        print(
            "=== /ask ERROR ===",
            flush=True
        )

        print(
            f"Exception Type: "
            f"{type(e).__name__}",
            flush=True
        )

        print(
            f"Exception Message: "
            f"{str(e)}",
            flush=True
        )

        print(
            f"[TIMING] /ask failed after: "
            f"{total_elapsed:.2f}s",
            flush=True
        )

        print(
            "Full traceback:",
            flush=True
        )

        traceback.print_exc()

        return {
            "error": str(e),
            "error_type": type(e).__name__,
        }


# ============================================================
# STATS ENDPOINT
# ============================================================

@app.get("/stats")
def stats():

    client = get_client()

    count_result = client.count(
        collection_name=COLLECTION_NAME,
        exact=True,
    )

    return {
        "points": count_result.count
    }


# ============================================================
# HOME / UI
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
def home():

    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "ui",
            "index.html",
        )
    ) as f:

        return f.read()