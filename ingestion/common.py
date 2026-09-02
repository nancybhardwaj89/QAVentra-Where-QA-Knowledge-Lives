import os
import uuid
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.http import models

COLLECTION_NAME = "qaventra"
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

_model = None
_client = None


def normalize_path(path):
    """Ensures file paths always use forward slashes, so the same file never
    produces two different chunk IDs depending on whether the path was built
    with / or \\ (this caused duplicate entries in Qdrant on Windows)."""
    return path.replace("\\", "/")


def get_model():
    global _model
    if _model is None:
        print("Loading BGE-M3 model...")
        _model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)  # CPU mode
    return _model

def get_client():
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
        if not _client.collection_exists(COLLECTION_NAME):
            _client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config={"dense": models.VectorParams(size=1024, distance=models.Distance.COSINE)},
                sparse_vectors_config={"sparse": models.SparseVectorParams()}
            )
            print(f"Created collection '{COLLECTION_NAME}'")
    return _client

def embed_and_upsert(chunks, batch_size=16):
    """
    chunks: list of dicts, each with:
        - "text": the chunk text
        - "payload": dict of metadata (source_type, file_path, etc.)
        - "id_seed": a string used to build a stable, deterministic point ID
    """
    model = get_model()
    client = get_client()
    total = 0

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        texts = [c["text"] for c in batch]

        output = model.encode(texts, return_dense=True, return_sparse=True, return_colbert_vecs=False)

        points = []
        for i, (dense_vec, lexical_weights) in enumerate(zip(output["dense_vecs"], output["lexical_weights"])):
            chunk = batch[i]
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["id_seed"]))
            sparse_indices = [int(k) for k in lexical_weights.keys()]
            sparse_values = [float(v) for v in lexical_weights.values()]

            payload = dict(chunk["payload"])
            payload["text"] = chunk["text"]

            points.append(models.PointStruct(
                id=point_id,
                vector={
                    "dense": dense_vec.tolist(),
                    "sparse": models.SparseVector(indices=sparse_indices, values=sparse_values)
                },
                payload=payload
            ))

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        total += len(points)
        print(f"Upserted {total}/{len(chunks)} chunks...")

    return total

def delete_by_filter(field: str, value: str):
    """Deletes every point in the collection whose payload[field] == value.
    Used to clean up all chunks belonging to a file/row/ticket that no
    longer exists in the source."""
    client = get_client()
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key=field, match=models.MatchValue(value=value))]
            )
        )
    )