"""
Video Assembly Service — FFmpeg Pipeline
Składa finalny film z komponentów:
- Voice track (ElevenLabs MP3)
- B-roll assets (Pexels/DALL-E images + short clips)
- Background music (Eleven Music / Suno)
- Captions (SRT burned in or soft)
- Intro/outro templates
- Transition effects

Renderuje do H.264 MP4, 1080p, 30fps.
"""
import asyncio
import tempfile
import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import httpx
import structlog

from services.storage_service import storage_service
from services.asset_service import asset_service

logger = structlog.get_logger(__name__)

# FFmpeg output profiles
PROFILES = {
    "youtube_1080p": {
        "resolution": "1920x1080",
        "fps": "30",
        "video_codec": "libx264",
        "crf": "20",
        "preset": "medium",
        "audio_codec": "aac",
        "audio_bitrate": "192k",
        "container": "mp4",
    },
    "youtube_shorts": {
        "resolution": "1080x1920",
        "fps": "30",
        "video_codec": "libx264",
        "crf": "20",
        "preset": "medium",
        "audio_codec": "aac",
        "audio_bitrate": "192k",
        "container": "mp4",
    },
    "preview_720p": {
        "resolution": "1280x720",
        "fps": "30",
        "video_codec": "libx264",
        "crf": "28",
        "preset": "fast",
        "audio_codec": "aac",
        "audio_bitrate": "128k",
        "container": "mp4",
    },
}


class VideoAssemblyService:
    def __init__(self):
        self.tmp_dir = Path(tempfile.gettempdir()) / "ytautos_render"
        self.tmp_dir.mkdir(exist_ok=True)

    async def assemble(
        self,
        voice_track_url: str,
        storyboard: List[Dict],
        assets: List[Dict],
        music_url: Optional[str] = None,
        captions_srt: Optional[str] = None,
        video_project_id: Optional[str] = None,
        profile: str = "youtube_1080p",
        output_format: str = "long_form",
    ) -> Dict:
        """
        Full video assembly pipeline.
        Returns {video_url, duration_seconds, size_bytes}.
        """
        import ffmpeg

        job_id = video_project_id or f"render_{asyncio.get_event_loop().time():.0f}"
        work_dir = self.tmp_dir / job_id
        work_dir.mkdir(exist_ok=True)

        logger.info("Video assembly started", job_id=job_id, profile=profile)

        try:
            # 1. Download voice track
            voice_path = work_dir / "voice.mp3"
            await self._download_asset(voice_track_url, voice_path)

            # 2. Get voice duration
            voice_duration = await self._get_audio_duration(str(voice_path))

            # 3. Download + prepare B-roll assets
            scene_videos = await self._prepare_scenes(
                storyboard, assets, work_dir, voice_duration
            )

            # 4. Build video timeline with ffmpeg-python
            output_path = work_dir / f"output_{job_id}.mp4"
            await self._render_video(
                voice_path=str(voice_path),
                scene_videos=scene_videos,
                output_path=str(output_path),
                captions_srt=captions_srt,
                music_url=music_url,
                work_dir=work_dir,
                profile=PROFILES.get(profile, PROFILES["youtube_1080p"]),
            )

            # 5. Upload to R2
            key = f"videos/{video_project_id or 'standalone'}/final.mp4"
            video_url = await storage_service.upload_file(str(output_path), key, "video/mp4")

            # 6. Get final duration
            final_duration = await self._get_video_duration(str(output_path))
            size_bytes = output_path.stat().st_size

            logger.info(
                "Video assembly complete",
                job_id=job_id,
                duration=final_duration,
                size_mb=round(size_bytes / 1024 / 1024, 1),
                url=video_url,
            )

            return {
                "video_url": video_url,
                "duration_seconds": final_duration,
                "size_bytes": size_bytes,
                "profile": profile,
            }

        except Exception as e:
            logger.error("Video assembly failed", job_id=job_id, error=str(e))
            raise
        finally:
            # Cleanup temp files
            import shutil
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

    async def _prepare_scenes(
        self,
        storyboard: List[Dict],
        assets: List[Dict],
        work_dir: Path,
        total_duration: float,
    ) -> List[Dict]:
        """
        Download and prepare B-roll for each scene.
        Returns list of {path, start_time, end_time, text_overlay}.
        """
        scenes = []
        assets_by_scene = {a.get("scene_index"): a for a in assets}

        current_time = 0.0
        for i, scene in enumerate(storyboard):
            scene_duration = float(scene.get("duration_seconds", total_duration / len(storyboard)))
            asset = assets_by_scene.get(i, {})

            asset_url = asset.get("url") or asset.get("image_url")
            scene_path = None

            if asset_url:
                ext = "mp4" if asset.get("type") == "video" else "jpg"
                scene_path = work_dir / f"scene_{i:03d}.{ext}"
                try:
                    await self._download_asset(asset_url, scene_path)
                except Exception as e:
                    logger.warning("Asset download failed", scene=i, error=str(e))
                    scene_path = None

            scenes.append({
                "index": i,
                "path": str(scene_path) if scene_path else None,
                "start_time": current_time,
                "end_time": current_time + scene_duration,
                "duration": scene_duration,
                "text_overlay": scene.get("overlay_text", ""),
                "type": asset.get("type", "image") if asset_url else "black",
            })
            current_time += scene_duration

        return scenes

    async def _render_video(
        self,
        voice_path: str,
        scene_videos: List[Dict],
        output_path: str,
        captions_srt: Optional[str],
        music_url: Optional[str],
        work_dir: Path,
        profile: Dict,
    ):
        """Build FFmpeg command and execute."""
        import subprocess

        # Build FFmpeg filter complex
        inputs = ["-i", voice_path]
        filter_parts = []
        concat_parts = []

        for i, scene in enumerate(scene_videos):
            if scene["path"] and os.path.exists(scene["path"]):
                if scene["type"] == "image":
                    # Loop image for scene duration
                    inputs.extend([
                        "-loop", "1",
                        "-t", str(scene["duration"]),
                        "-i", scene["path"],
                    ])
                else:
                    inputs.extend(["-i", scene["path"]])

                vid_idx = (i + 1) * 2  # offset for voice track at index 0
                filter_parts.append(
                    f"[{i + 1}:v]scale={profile['resolution']},setsar=1[v{i}]"
                )
                concat_parts.append(f"[v{i}]")
            else:
                # Black frame as fallback
                filter_parts.append(
                    f"color=black:s={profile['resolution']}:d={scene['duration']}[v{i}]"
                )
                concat_parts.append(f"[v{i}]")

        n_scenes = len(scene_videos)
        filter_complex = ";".join(filter_parts)
        filter_complex += f";{''.join(concat_parts)}concat=n={n_scenes}:v=1:a=0[vout]"

        # Add music if provided
        audio_filter = "[0:a]"
        if music_url:
            music_path = work_dir / "music.mp3"
            await self._download_asset(music_url, music_path)
            inputs.extend(["-i", str(music_path)])
            music_idx = n_scenes + 1
            # Duck music under voice: voice at 1.0, music at 0.12
            filter_complex += f";[0:a]volume=1.0[voice];[{music_idx}:a]volume=0.12[music];[voice][music]amix=inputs=2:duration=first[aout]"
            audio_filter = "[aout]"

        # Burn-in captions if provided
        if captions_srt:
            srt_path = work_dir / "captions.srt"
            srt_path.write_text(captions_srt, encoding="utf-8")
            filter_complex += f";[vout]subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Bold=1,Outline=2'[vfinal]"
            video_out = "[vfinal]"
        else:
            video_out = "[vout]"

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", video_out,
            "-map", audio_filter,
            "-c:v", profile["video_codec"],
            "-crf", profile["crf"],
            "-preset", profile["preset"],
            "-c:a", profile["audio_codec"],
            "-b:a", profile["audio_bitrate"],
            "-movflags", "+faststart",  # Streaming optimization
            "-pix_fmt", "yuv420p",
            output_path,
        ]

        logger.debug("FFmpeg command", cmd=" ".join(cmd[:10]) + "...")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise Exception(f"FFmpeg failed: {stderr.decode()[-500:]}")

    async def generate_captions(self, voice_track_url: str) -> str:
        """
        Generate SRT captions using Whisper API.
        Returns SRT string.
        """
        import httpx

        voice_path = self.tmp_dir / "caption_audio.mp3"
        await self._download_asset(voice_track_url, voice_path)

        async with httpx.AsyncClient() as client:
            with open(voice_path, "rb") as f:
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {__import__('core.config', fromlist=['settings']).settings.openai_api_key}"},
                    data={"model": "whisper-1", "response_format": "srt", "language": "pl"},
                    files={"file": ("audio.mp3", f, "audio/mpeg")},
                    timeout=120.0,
                )

        if response.status_code == 200:
            return response.text
        raise Exception(f"Whisper transcription failed: {response.status_code}")

    async def _download_asset(self, url: str, dest_path: Path):
        """Download file from URL to local path."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            dest_path.write_bytes(response.content)

    @staticmethod
    async def _get_audio_duration(path: str) -> float:
        """Get audio duration using ffprobe."""
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        try:
            data = json.loads(stdout)
            return float(data["streams"][0]["duration"])
        except Exception:
            return 600.0  # default 10 min

    @staticmethod
    async def _get_video_duration(path: str) -> float:
        """Get video duration using ffprobe."""
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        try:
            data = json.loads(stdout)
            return float(data["format"]["duration"])
        except Exception:
            return 0.0


video_assembly_service = VideoAssemblyService()
