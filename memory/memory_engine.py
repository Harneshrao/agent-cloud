"""
In-memory store using ChromaDB. Optional: if ChromaDB/NumPy are unavailable
(e.g. Python 3.14 without compatible wheels), memory is disabled and the worker still runs.
"""

_client = None
_collection = None

try:
    import chromadb
    _client = chromadb.Client()
    _collection = _client.get_or_create_collection(name="agent_memory")
except Exception:
    _client = None
    _collection = None


def store_memory(text):
    if _collection is None:
        return
    _collection.add(
        documents=[text],
        ids=[str(hash(text))],
    )


def search_memory(query):
    if _collection is None:
        return []
    results = _collection.query(
        query_texts=[query],
        n_results=2,
    )
    return results.get("documents", []) or []
