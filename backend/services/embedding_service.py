"""
Embedding Service — pgvector similarity search
Real implementation using OpenAI text-embedding-3-large (1536 dims).

Core operations:
1. embed_text() — generate 1536-dim vector for any text
2. find_similar_scripts() — cosine search in DB
3. find_similar_videos() — cross-video similarity
4. rebuild_channel_embeddings() — batch rebuild for a channel
"""
from typing import List, Dict, Optional, Tuple
import asyncio
import structlog
from openai import AsyncOpenAI

from core.config import settings
from core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)

# Cosine distance operator in pgvector: <=> (lower = more similar)
# similarity = 1 - cosine_distance


class EmbeddingService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            organization=settings.openai_org_id or None,
        )
        self.model = settings.openai_embedding_model  # text-embedding-3-large
        self.dimensions = 1536

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for text. Returns 1536-dim list."""
        if not text or not text.strip():
            return [0.0] * self.dimensions

        try:
            # Truncate to 8191 tokens (model limit)
            text_truncated = text[:32000]
            response = await self.client.embeddings.create(
                model=self.model,
                input=text_truncated,
                dimensions=self.dimensions,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            return [0.0] * self.dimensions

    async def embed_script(self, script_text: str, script_id: str) -> bool:
        """Embed script and store in DB."""
        from sqlalchemy import text
        from uuid import UUID

        embedding = await self.embed_text(script_text)
        if not any(embedding):
            return False

        # Convert to PostgreSQL vector format: [0.1, 0.2, ...]
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

        async with AsyncSessionLocal() as db:
            await db.execute(
                text("UPDATE scripts SET content_embedding = :vec::vector WHERE id = :id"),
                {"vec": vector_str, "id": UUID(script_id)},
            )
            await db.commit()

        logger.debug("Script embedded", script_id=script_id)
        return True

    async def embed_video_project(self, combined_text: str, video_id: str) -> bool:
        """Embed video project (title + keywords + script excerpt)."""
        from sqlalchemy import text
        from uuid import UUID

        embedding = await self.embed_text(combined_text)
        if not any(embedding):
            return False

        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

        async with AsyncSessionLocal() as db:
            await db.execute(
                text(
                    "UPDATE video_projects SET content_embedding_vec = :vec::vector WHERE id = :id"
                ),
                {"vec": vector_str, "id": UUID(video_id)},
            )
            await db.commit()

        return True

    async def find_similar_scripts(
        self,
        script_text: str,
        channel_id: str,
        exclude_script_id: Optional[str] = None,
        top_k: int = 5,
        threshold: float = None,
    ) -> List[Dict]:
        """
        Find scripts similar to given text in the same channel.
        Returns list of {script_id, title, similarity} sorted by similarity DESC.

        Uses pgvector cosine distance: 1 - (embedding <=> query_vector)
        """
        from sqlalchemy import text
        from uuid import UUID

        if threshold is None:
            threshold = settings.max_similarity_cosine

        query_embedding = await self.embed_text(script_text)
        if not any(query_embedding):
            return []

        vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        exclude_clause = ""
        params: dict = {"vec": vector_str, "channel_id": UUID(channel_id), "top_k": top_k}

        if exclude_script_id:
            exclude_clause = "AND s.id != :exclude_id"
            params["exclude_id"] = UUID(exclude_script_id)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text(f"""
                    SELECT
                        s.id,
                        s.title,
                        vp.title as video_title,
                        1 - (s.content_embedding <=> :vec::vector) AS similarity
                    FROM scripts s
                    JOIN video_projects vp ON s.video_project_id = vp.id
                    WHERE vp.channel_id = :channel_id
                      AND s.content_embedding IS NOT NULL
                      {exclude_clause}
                    ORDER BY s.content_embedding <=> :vec::vector
                    LIMIT :top_k
                """),
                params,
            )
            rows = result.fetchall()

        return [
            {
                "script_id": str(row.id),
                "script_title": row.title,
                "video_title": row.video_title,
                "similarity": round(float(row.similarity), 4),
                "above_threshold": float(row.similarity) >= threshold,
            }
            for row in rows
        ]

    async def find_similar_videos(
        self,
        channel_id: str,
        threshold: float = None,
    ) -> List[Dict]:
        """
        Find all pairs of videos in a channel with cosine similarity > threshold.
        Used for weekly compliance scan — detect template farm patterns.
        """
        from sqlalchemy import text
        from uuid import UUID

        if threshold is None:
            threshold = settings.max_similarity_cosine

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT
                        a.id as video_a_id,
                        a.title as video_a_title,
                        b.id as video_b_id,
                        b.title as video_b_title,
                        1 - (a.content_embedding_vec <=> b.content_embedding_vec) AS similarity
                    FROM video_projects a
                    CROSS JOIN video_projects b
                    WHERE a.channel_id = :channel_id
                      AND b.channel_id = :channel_id
                      AND a.id < b.id
                      AND a.content_embedding_vec IS NOT NULL
                      AND b.content_embedding_vec IS NOT NULL
                      AND 1 - (a.content_embedding_vec <=> b.content_embedding_vec) >= :threshold
                    ORDER BY similarity DESC
                    LIMIT 20
                """),
                {"channel_id": UUID(channel_id), "threshold": threshold},
            )
            rows = result.fetchall()

        return [
            {
                "video_a_id": str(row.video_a_id),
                "video_a_title": row.video_a_title,
                "video_b_id": str(row.video_b_id),
                "video_b_title": row.video_b_title,
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]

    async def rebuild_channel_embeddings(self, channel_id: str) -> int:
        """
        Batch-rebuild embeddings for all scripts in a channel that lack them.
        Returns count of rebuilt embeddings.
        """
        from sqlalchemy import text
        from uuid import UUID

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT s.id, s.full_text
                    FROM scripts s
                    JOIN video_projects vp ON s.video_project_id = vp.id
                    WHERE vp.channel_id = :channel_id
                      AND s.content_embedding IS NULL
                      AND s.full_text IS NOT NULL
                    LIMIT 100
                """),
                {"channel_id": UUID(channel_id)},
            )
            scripts = result.fetchall()

        rebuilt = 0
        for script in scripts:
            if script.full_text:
                success = await self.embed_script(script.full_text, str(script.id))
                if success:
                    rebuilt += 1
                await asyncio.sleep(0.1)  # rate limiting

        logger.info("Channel embeddings rebuilt", channel_id=channel_id, count=rebuilt)
        return rebuilt

    async def compute_originality_score(
        self,
        script_text: str,
        channel_id: str,
        exclude_script_id: Optional[str] = None,
    ) -> Tuple[float, List[Dict]]:
        """
        Compute originality score for new script.
        Returns (originality_score 0-100, similar_scripts).

        Formula: originality = (1 - max_similarity) * 100
        If max_similarity < 0.5 → score 95+
        If max_similarity 0.5-0.7 → score 70-90
        If max_similarity 0.7-0.85 → score 50-70 (yellow)
        If max_similarity > 0.85 → score < 50 (red flag)
        """
        similar = await self.find_similar_scripts(
            script_text, channel_id, exclude_script_id, top_k=5
        )

        if not similar:
            return 95.0, []

        max_similarity = max(s["similarity"] for s in similar)

        # Non-linear mapping: small similarity = high originality
        if max_similarity < 0.3:
            originality = 97.0
        elif max_similarity < 0.5:
            originality = 90.0 + (0.5 - max_similarity) * 20
        elif max_similarity < 0.7:
            originality = 75.0 + (0.7 - max_similarity) * 75
        elif max_similarity < 0.85:
            originality = 50.0 + (0.85 - max_similarity) * 166
        else:
            originality = max(0.0, 50.0 - (max_similarity - 0.85) * 333)

        return round(originality, 1), similar


embedding_service = EmbeddingService()
