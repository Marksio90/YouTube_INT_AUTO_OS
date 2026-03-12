"""
Storage Service — Cloudflare R2 (S3-compatible)
Handles all file uploads: voice tracks, thumbnails, videos, assets.

R2 pricing: 1TB stored + 10TB egress = ~$15/msc (vs $914/msc AWS S3)
Zero egress fees — perfect for video content.
"""
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional
import structlog

from core.config import settings

logger = structlog.get_logger(__name__)


class StorageService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if not self._client:
            if not settings.r2_access_key_id:
                raise ValueError("Cloudflare R2 credentials not configured")
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.r2_endpoint_url,
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "adaptive"},
                ),
            )
        return self._client

    async def upload(
        self,
        data: bytes,
        key: str,
        content_type: str = "application/octet-stream",
        public: bool = True,
    ) -> str:
        """Upload bytes to R2. Returns public URL."""
        import asyncio
        loop = asyncio.get_running_loop()

        extra_args = {"ContentType": content_type}
        if public:
            extra_args["ACL"] = "public-read"

        await loop.run_in_executor(
            None,
            lambda: self.client.put_object(
                Bucket=settings.r2_bucket_name,
                Key=key,
                Body=data,
                **extra_args,
            ),
        )

        return self._public_url(key)

    async def upload_file(self, local_path: str, key: str, content_type: str = "video/mp4") -> str:
        """Upload local file to R2. Returns public URL."""
        import asyncio
        loop = asyncio.get_running_loop()

        await loop.run_in_executor(
            None,
            lambda: self.client.upload_file(
                local_path,
                settings.r2_bucket_name,
                key,
                ExtraArgs={"ContentType": content_type},
            ),
        )

        return self._public_url(key)

    async def get_url_if_exists(self, key: str) -> Optional[str]:
        """Check if file exists. Returns URL or None."""
        import asyncio
        loop = asyncio.get_running_loop()

        try:
            await loop.run_in_executor(
                None,
                lambda: self.client.head_object(Bucket=settings.r2_bucket_name, Key=key),
            )
            return self._public_url(key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            raise

    async def delete(self, key: str) -> bool:
        """Delete file from R2."""
        import asyncio
        loop = asyncio.get_running_loop()

        try:
            await loop.run_in_executor(
                None,
                lambda: self.client.delete_object(Bucket=settings.r2_bucket_name, Key=key),
            )
            return True
        except Exception as e:
            logger.error("Failed to delete object from R2", key=key, error=str(e))
            return False

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for temporary access (uploads from browser)."""
        import asyncio
        loop = asyncio.get_running_loop()

        url = await loop.run_in_executor(
            None,
            lambda: self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.r2_bucket_name, "Key": key},
                ExpiresIn=expires_in,
            ),
        )
        return url

    def _public_url(self, key: str) -> str:
        """Construct public URL for R2 object."""
        # R2 public bucket URL format
        endpoint = settings.r2_endpoint_url.replace(
            f"https://{settings.r2_access_key_id[:32]}.r2.cloudflarestorage.com", ""
        )
        return f"{settings.r2_endpoint_url}/{settings.r2_bucket_name}/{key}"


storage_service = StorageService()
