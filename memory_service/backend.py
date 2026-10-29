"""Mem0 storage adapter: local embeddings only, never instantiate Mem0 Memory/LLMs."""

import hashlib
import logging
import os
from uuid import NAMESPACE_URL, uuid5

from memory_service.app import RevisionConflict

MODEL = "intfloat/multilingual-e5-small"
REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
DIMENSIONS = 384


class Mem0Index:
    def __init__(self, store, embedder, lock_pool):
        self.store = store
        self.embedder = embedder
        self.lock_pool = lock_pool

    @classmethod
    def from_environment(cls):
        # No Memory() constructor: it creates default LLM, telemetry and history clients.
        os.environ["MEM0_TELEMETRY"] = "false"
        from mem0.vector_stores.pgvector import PGVector
        from psycopg.conninfo import make_conninfo
        from psycopg_pool import ConnectionPool
        from sentence_transformers import SentenceTransformer

        logging.getLogger("mem0.vector_stores.pgvector").disabled = True
        conninfo = make_conninfo(
            host=os.environ["MEMORY_DB_HOST"],
            port=os.environ.get("MEMORY_DB_PORT", "5432"),
            dbname=os.environ.get("MEMORY_DB_NAME", "memory_index"),
            user=os.environ.get("MEMORY_DB_USER", "memory_index"),
            password=os.environ["MEMORY_DB_PASSWORD"],
            connect_timeout=5,
            options="-c statement_timeout=10000 -c lock_timeout=5000",
        )
        pool = ConnectionPool(conninfo, min_size=1, max_size=4, timeout=5, open=True)
        store = PGVector(
            dbname="memory_index",
            collection_name="canonical_memory",
            embedding_model_dims=DIMENSIONS,
            user=None,
            password=None,
            host=None,
            port=None,
            diskann=False,
            hnsw=False,
            connection_string=conninfo,
            minconn=1,
            maxconn=4,
        )
        # The model is fetched at image build using a full immutable revision. At
        # runtime both offline mode and local_files_only prevent network downloads.
        embedder = SentenceTransformer(
            MODEL,
            revision=REVISION,
            device="cpu",
            trust_remote_code=False,
            local_files_only=True,
        )
        if embedder.get_embedding_dimension() != DIMENSIONS:
            raise RuntimeError("Unexpected embedding dimensions")
        backend = cls(store, embedder, pool)
        backend.health()
        return backend

    @staticmethod
    def key(record):
        return str(
            uuid5(
                NAMESPACE_URL,
                f"thecommander-memory:{record.owner_id}:{record.project_id}:{record.id}",
            )
        )

    def vector(self, text, *, query=False):
        prefixed = ("query: " if query else "passage: ") + text
        tokens = self.embedder.tokenizer(
            prefixed, truncation=False, add_special_tokens=True, verbose=False
        )["input_ids"]
        limit = min(512, self.embedder.max_seq_length)
        truncated = len(tokens) > limit
        # SentenceTransformer's tokenizer truncates deterministically to its
        # configured sequence length, preserving special tokens and E5 prefix.
        self.embedder.max_seq_length = limit
        vector = self.embedder.encode(
            prefixed, normalize_embeddings=True, show_progress_bar=False
        ).tolist()
        return vector, truncated

    def health(self):
        # Readiness proves the initialized collection is accessible, not retrieval quality.
        self.store.col_info()

    def upsert(self, record):
        vector, truncated = self.vector(record.text)
        key = self.key(record)
        # Serialize revisions across processes/replicas. The lock is held on a
        # separate connection while Mem0 performs its own short transactions.
        with self.lock_pool.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (key,))
            existing = self.store.get(key)
            payload = {
                "owner_id": str(record.owner_id),
                "project_id": str(record.project_id) if record.project_id else "owner",
                "canonical_id": str(record.id),
                "revision": record.revision,
                "deleted": False,
                "content_hash": hashlib.sha256(record.text.encode()).hexdigest(),
                "text_lemmatized": record.text,
            }
            if existing:
                old = existing.payload or {}
                if (
                    (old.get("deleted") and int(old.get("revision", 0)) >= record.revision)
                    or int(old.get("revision", 0)) > record.revision
                    or (
                        int(old.get("revision", 0)) == record.revision
                        and old.get("content_hash") != payload["content_hash"]
                    )
                ):
                    raise RevisionConflict()
                self.store.update(key, vector=vector, payload=payload)
            else:
                self.store.insert([vector], payloads=[payload], ids=[key])

        return truncated

    def delete(self, record):
        key = self.key(record)
        with self.lock_pool.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (key,))
            existing = self.store.get(key)
            payload = {
                "owner_id": str(record.owner_id),
                "project_id": str(record.project_id) if record.project_id else "owner",
                "canonical_id": str(record.id),
                "revision": record.revision,
                "deleted": True,
            }
            if existing:
                if int((existing.payload or {}).get("revision", 0)) > record.revision:
                    raise RevisionConflict()
                self.store.update(key, vector=[0.0] * DIMENSIONS, payload=payload)
            else:
                self.store.insert([[0.0] * DIMENSIONS], payloads=[payload], ids=[key])

    def search(self, query):
        filters = {
            "deleted": False,
            "owner_id": str(query.owner_id),
            "project_id": str(query.project_id) if query.project_id else "owner",
        }
        vector, query_truncated = self.vector(query.query, query=True)
        semantic = self.store.search(query.query, vector, top_k=query.limit, filters=filters)
        lexical = self.store.keyword_search(query.query, top_k=query.limit, filters=filters)
        if lexical is None:
            raise RuntimeError("Lexical retrieval unavailable")
        # Reciprocal rank fusion. This score expresses rank, not factual confidence.
        scores = {}
        for results in (semantic, lexical):
            for rank, item in enumerate(results, start=1):
                payload = item.payload or {}
                # Defense in depth if a backend/configuration returns another scope.
                if any(payload.get(k) != v for k, v in filters.items()):
                    continue
                key = (payload["canonical_id"], payload["revision"])
                scores[key] = scores.get(key, 0.0) + 1 / (60 + rank)
        return {
            "hits": [
                {"id": key[0], "revision": key[1], "score": scores[key]}
                for key in sorted(scores, key=lambda key: (-scores[key], key[0]))[: query.limit]
            ],
            "query_truncated": query_truncated,
        }

    def close(self):
        self.lock_pool.close()
        self.store.connection_pool.close()
