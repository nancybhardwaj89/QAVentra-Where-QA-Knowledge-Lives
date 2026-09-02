import os
from dotenv import load_dotenv
from FlagEmbedding import BGEM3FlagModel
from sentence_transformers import CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.http import models

load_dotenv()

COLLECTION_NAME = "qaventra"
client = QdrantClient(url="http://localhost:6333")

print("Loading models...")
embed_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)

# --- ASK A QUESTION ---
question = "How is patient registration handled in the PRD, and is there a test automation script for it?"

q_output = embed_model.encode([question], return_dense=True, return_sparse=True)
q_dense = q_output["dense_vecs"][0]
q_sparse = q_output["lexical_weights"][0]

# --- HYBRID SEARCH (dense + sparse, Qdrant fuses both) ---
results = client.query_points(
    collection_name=COLLECTION_NAME,
    prefetch=[
        models.Prefetch(query=q_dense.tolist(), using="dense", limit=25),
        models.Prefetch(
            query=models.SparseVector(
                indices=[int(k) for k in q_sparse.keys()],
                values=[float(v) for v in q_sparse.values()]
            ),
            using="sparse",
            limit=25
        )
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF),
    limit=25
).points

print(f"\nHybrid search returned {len(results)} candidates. Reranking...\n")

# --- RERANK ---
pairs = [(question, r.payload["text"]) for r in results]
scores = reranker.predict(pairs)

reranked = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)
top_results = reranked[:5]

print("=== TOP 5 RESULTS AFTER RERANKING ===\n")
for r, score in top_results:
    source_type = r.payload.get("source_type", "unknown")
    identifier = (
        r.payload.get("test_case_id")
        or r.payload.get("file_path")
        or r.payload.get("ticket_id")
        or "unknown"
    )
    print(f"Score: {score:.4f} | Source: {source_type} | ID: {identifier}")
    print(r.payload["text"])
    print("-" * 60)