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

    def _to_pgvector_str(self, embedding: List[float]) -> str:
        """Convert float list to pgvector string. Validates all values are finite floats."""
        import math
        sanitized = []
        for v in embedding:
            if not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f"Invalid embedding value: {v!r}")
            sanitized.append(float(v))
        return "[" + ",".join(f"{v:.8f}" for v in sanitized) + "]"

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
            raise RuntimeError(f"Embedding generation failed: {e}") from e

    async def embed_script(self, script_text: str, script_id: str) -> bool:
        """Embed script and store in DB."""
        from sqlalchemy import text
        from uuid import UUID

        try:
            embedding = await self.embed_text(script_text)
            vector_str = self._to_pgvector_str(embedding)
        except Exception as e:
            logger.error("Failed to generate/validate embedding for script", script_id=script_id, error=str(e))
            return False

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

        try:
            embedding = await self.embed_text(combined_text)
            vector_str = self._to_pgvector_str(embedding)
        except Exception as e:
            logger.error("Failed to generate/validate embedding for video", video_id=video_id, error=str(e))
            return False

        async with AsyncSessionLocal() as db:
            await db.execute(
                text(
                    "UPDATE video_projects SET content_embedding = :vec::vector WHERE id = :id"
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

        try:
            query_embedding = await self.embed_text(script_text)
            vector_str = self._to_pgvector_str(query_embedding)
        except Exception as e:
            logger.error("Failed to generate query embedding", error=str(e))
            return []

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
        max_videos: int = 200,
    ) -> List[Dict]:
        """
        Find pairs of videos in a channel with cosine similarity > threshold.
        Used for weekly compliance scan — detect template farm patterns.

        Uses a two-pass approach to avoid O(n²) CROSS JOIN on large channels:
        1. Fetch all embedded videos for the channel (up to max_videos)
        2. For each video, use pgvector <=> operator to find its nearest neighbors
        This results in O(n * k) queries instead of O(n²) rows in memory.
        """
        from sqlalchemy import text
        from uuid import UUID

        if threshold is None:
            threshold = settings.max_similarity_cosine

        if not (0.0 <= threshold <= 1.0):
            raise ValueError(f"threshold must be between 0.0 and 1.0, got {threshold}")

        async with AsyncSessionLocal() as db:
            # Step 1: Fetch all videos with embeddings for this channel
            result = await db.execute(
                text("""
                    SELECT id, title, content_embedding
                    FROM video_projects
                    WHERE channel_id = :channel_id
                      AND content_embedding IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT :max_videos
                """),
                {"channel_id": UUID(channel_id), "max_videos": max_videos},
            )
            videos = result.fetchall()

        if len(videos) < 2:
            return []

        # Step 2: For each video, find similar ones using indexed <=> operator
        seen_pairs: set = set()
        similar_pairs: List[Dict] = []

        async with AsyncSessionLocal() as db:
            for video in videos:
                result = await db.execute(
                    text("""
                        SELECT
                            id,
                            title,
                            1 - (content_embedding <=> :vec::vector) AS similarity
                        FROM video_projects
                        WHERE channel_id = :channel_id
                          AND id != :exclude_id
                          AND content_embedding IS NOT NULL
                          AND 1 - (content_embedding <=> :vec::vector) >= :threshold
                        ORDER BY content_embedding <=> :vec::vector
                        LIMIT 5
                    """),
                    {
                        "vec": str(video.content_embedding),
                        "channel_id": UUID(channel_id),
                        "exclude_id": video.id,
                        "threshold": threshold,
                    },
                )
                neighbors = result.fetchall()

                for neighbor in neighbors:
                    # Deduplicate pairs (a,b) == (b,a)
                    pair_key = tuple(sorted([str(video.id), str(neighbor.id)]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    similar_pairs.append({
                        "video_a_id": str(video.id),
                        "video_a_title": video.title,
                        "video_b_id": str(neighbor.id),
                        "video_b_title": neighbor.title,
                        "similarity": round(float(neighbor.similarity), 4),
                    })

        # Return top pairs by similarity
        similar_pairs.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_pairs[:50]

    async def rebuild_channel_embeddings(self, channel_id: str, batch_size: int = 50) -> int:
        """
        Batch-rebuild embeddings for all scripts in a channel that lack them.
        Processes all scripts in batches to avoid memory issues on large channels.
        Returns total count of rebuilt embeddings.
        """
        from sqlalchemy import text
        from uuid import UUID

        rebuilt = 0
        offset = 0

        while True:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT s.id, s.full_text
                        FROM scripts s
                        JOIN video_projects vp ON s.video_project_id = vp.id
                        WHERE vp.channel_id = :channel_id
                          AND s.content_embedding IS NULL
                          AND s.full_text IS NOT NULL
                        ORDER BY s.created_at ASC
                        LIMIT :batch_size OFFSET :offset
                    """),
                    {"channel_id": UUID(channel_id), "batch_size": batch_size, "offset": offset},
                )
                scripts = result.fetchall()

            if not scripts:
                break

            for script in scripts:
                if script.full_text:
                    success = await self.embed_script(script.full_text, str(script.id))
                    if success:
                        rebuilt += 1
                    await asyncio.sleep(0.1)  # rate limiting

            offset += batch_size
            logger.debug("Embedding batch done", channel_id=channel_id, offset=offset, rebuilt_so_far=rebuilt)

        logger.info("Channel embeddings rebuilt", channel_id=channel_id, total=rebuilt)
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
