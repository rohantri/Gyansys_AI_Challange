"""Step two. Search the grounded catalogue.

No vector database. At a few thousand entries a numpy dot product takes
milliseconds and removes an entire dependency. ChromaDB pulls in onnxruntime,
FAISS adds thirty megabytes, and neither buys anything at this scale.

The catalogue is embedded once and cached by the caller. The query is embedded
at request time through the API, so nothing local has to load a model.
"""

import json
import numpy as np
from .llm import embed_documents, embed_query

SIMILARITY_FLOOR = 0.55


def load_catalogue(path: str):
    with open(path) as f:
        return json.load(f)


def entry_text(e: dict) -> str:
    """What gets embedded. Capability text carries most of the signal."""
    return (
        f"{e['name']}. {e['capability']} "
        f"Objects: {', '.join(e.get('objects', []))}. "
        f"Module: {e.get('module','')}. Tier: {e.get('tier','')}."
    )


def build_index(catalogue: dict):
    entries = catalogue["entries"]
    vectors = embed_documents([entry_text(e) for e in entries])
    matrix = np.array(vectors, dtype=np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix


def search(structured, catalogue, matrix, top_k: int = 8):
    """Returns (hits, simplification_flags, standard_match_found)."""
    query = (
        f"{structured.summary} "
        f"Objects: {', '.join(structured.business_objects)}. "
        f"Action: {structured.action_type}."
    )
    qv = np.array(embed_query(query), dtype=np.float32)
    qv /= np.linalg.norm(qv)

    scores = matrix @ qv
    order = np.argsort(-scores)[:top_k]

    entries = catalogue["entries"]
    hits = []
    for i in order:
        e = dict(entries[int(i)])
        e["score"] = round(float(scores[int(i)]), 3)
        hits.append(e)

    above_floor = [h for h in hits if h["score"] >= SIMILARITY_FLOOR]

    # A simplification item only counts as a flag if it shares a business object
    # with the requirement. Otherwise every query drags in unrelated blockers.
    req_objects = {o.lower() for o in structured.business_objects}
    simplification_flags = [
        h
        for h in above_floor
        if h["type"] == "simplification_item"
        and (req_objects & {o.lower() for o in h.get("objects", [])})
    ]

    standard_match_found = any(
        h["type"] == "standard_functionality" and h["score"] >= 0.62
        for h in above_floor
    )

    return hits, above_floor, simplification_flags, standard_match_found
