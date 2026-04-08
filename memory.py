"""Memory system using Voyage AI embeddings and sqlite-vec for vector storage."""

import json
import sqlite3
import struct
import time
from typing import Optional

import voyageai

import config


def _serialize_vector(vec: list[float]) -> bytes:
    """Serialize a float vector to bytes for sqlite-vec."""
    return struct.pack(f"{len(vec)}f", *vec)


class Memory:
    """Embed, store, and retrieve teacher context using Voyage + sqlite-vec."""

    def __init__(self, db_path: str = str(config.DB_PATH)):
        self.db_path = db_path
        self._voyage = None
        self.conn = sqlite3.connect(db_path)
        self.conn.enable_load_extension(True)
        self._load_sqlite_vec()
        self._init_tables()

    @property
    def voyage(self):
        """Lazy-init Voyage client so the module loads without an API key."""
        if self._voyage is None:
            self._voyage = voyageai.Client(api_key=config.VOYAGE_API_KEY)
        return self._voyage

    def _load_sqlite_vec(self):
        """Load the sqlite-vec extension."""
        try:
            import sqlite_vec

            self.conn.load_extension(sqlite_vec.loadable_path())
        except Exception as e:
            raise RuntimeError(
                f"Failed to load sqlite-vec: {e}\n"
                "Install with: pip install sqlite-vec"
            ) from e

    def _init_tables(self):
        """Create tables if they don't exist."""
        dim = config.EMBEDDING_DIM
        self.conn.executescript(f"""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT DEFAULT '',
                timestamp REAL NOT NULL,
                metadata TEXT DEFAULT '{{}}'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
                id INTEGER PRIMARY KEY,
                embedding float[{dim}]
            );
        """)
        self.conn.commit()

    def embed(self, text: str) -> list[float]:
        """Get embedding for a text string using Voyage."""
        result = self.voyage.embed(
            texts=[text],
            model=config.VOYAGE_MODEL,
            input_type="document",
        )
        return result.embeddings[0]

    def embed_query(self, text: str) -> list[float]:
        """Get embedding for a query string using Voyage."""
        result = self.voyage.embed(
            texts=[text],
            model=config.VOYAGE_MODEL,
            input_type="query",
        )
        return result.embeddings[0]

    def store(
        self,
        content: str,
        collection: str,
        category: str = "",
        metadata: Optional[dict] = None,
    ) -> int:
        """Store a memory with its embedding."""
        embedding = self.embed(content)
        timestamp = time.time()
        meta_json = json.dumps(metadata or {})

        cursor = self.conn.execute(
            "INSERT INTO memories (collection, content, category, timestamp, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (collection, content, category, timestamp, meta_json),
        )
        memory_id = cursor.lastrowid

        self.conn.execute(
            "INSERT INTO memory_vectors (id, embedding) VALUES (?, ?)",
            (memory_id, _serialize_vector(embedding)),
        )
        self.conn.commit()
        return memory_id

    def retrieve(
        self,
        query: str,
        collection: str,
        limit: int = config.MAX_MEMORY_RESULTS,
    ) -> list[dict]:
        """Retrieve memories by semantic similarity to query."""
        query_embedding = self.embed_query(query)

        rows = self.conn.execute(
            """
            SELECT m.id, m.content, m.category, m.timestamp, m.metadata, v.distance
            FROM memory_vectors v
            JOIN memories m ON m.id = v.id
            WHERE m.collection = ?
              AND v.embedding MATCH ?
            ORDER BY v.distance
            LIMIT ?
            """,
            (collection, _serialize_vector(query_embedding), limit),
        ).fetchall()

        return [
            {
                "id": row[0],
                "content": row[1],
                "category": row[2],
                "timestamp": row[3],
                "metadata": json.loads(row[4]),
                "distance": row[5],
            }
            for row in rows
        ]

    def get_all(self, collection: str) -> list[dict]:
        """Get all memories in a collection (used for teacher profile)."""
        rows = self.conn.execute(
            "SELECT id, content, category, timestamp, metadata "
            "FROM memories WHERE collection = ? ORDER BY timestamp",
            (collection,),
        ).fetchall()

        return [
            {
                "id": row[0],
                "content": row[1],
                "category": row[2],
                "timestamp": row[3],
                "metadata": json.loads(row[4]),
            }
            for row in rows
        ]

    def has_profile(self) -> bool:
        """Check if a teacher profile exists."""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE collection = ?",
            (config.PROFILE_COLLECTION,),
        ).fetchone()
        return row[0] > 0

    def store_exchange(self, teacher_msg: str, assistant_msg: str):
        """Store a conversation exchange."""
        combined = f"Teacher: {teacher_msg}\n\nAssistant: {assistant_msg}"
        self.store(
            content=combined,
            collection=config.CONVERSATION_COLLECTION,
            metadata={"teacher_msg": teacher_msg, "assistant_msg": assistant_msg},
        )

    def close(self):
        """Close the database connection."""
        self.conn.close()
