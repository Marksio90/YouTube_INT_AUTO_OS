"""
Video Assembly Service — FFmpeg Pipeline with Chunked Parallel Rendering.

Składa finalny film z komponentów:
- Voice track (ElevenLabs MP3)
- B-roll assets (Pexels/DALL-E images + short clips)
- Background music (Eleven Music / Suno)
- Captions (SRT burned in or soft)
- Intro/outro templates
- Transition effects

Renderuje do H.264 MP4, 1080p, 30fps.

Chunked Parallel Rendering (Map-Reduce):
- Divides scenes into N equal chunks (default: 4)
- Renders each chunk concurrently with asyncio.gather
- Concatenates chunks using ffmpeg concat demuxer
- Reduces render time by ~4x on multi-core machines
- Falls back to sequential rendering if any chunk fails

GPU Acceleration:
- Detects NVENC availability at startup
- Swaps libx264 → h264_nvenc when GPU is present
- Falls back to CPU transparently
"""
import asyncio
import tempfile
import os
import json
import math
from pathlib import Path
from typing import List, Dict, Optional
import httpx
import structlog

from services.storage_service import storage_service
from services.asset_service import asset_service
from core.langfuse import create_trace

logger = structlog.get_logger(__name__)

# ── GPU Acceleration Detection ──────────────────────────────────────────────
def _detect_gpu_encoder() -> str:
    """
    Check if NVENC is available. Returns 'h264_nvenc' or 'libx264'.
    Cached after first call.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=5
        )
        if "h264_nvenc" in result.stdout:
            return "h264_nvenc"
    except Exception:
        pass
    return "libx264"


_GPU_ENCODER: str = _detect_gpu_encoder()

# ── FFmpeg output profiles ────────────────────────────────────────────────────
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
    # How many parallel chunks to render (tune per machine CPU/GPU count)
    CHUNK_COUNT: int = 4
    # Minimum scenes per chunk before we bother parallelising
    MIN_SCENES_FOR_PARALLEL: int = 4

    def __init__(self):
        self.tmp_dir = Path(tempfile.gettempdir()) / "ytautos_render"
        self.tmp_dir.mkdir(exist_ok=True)
        logger.info(
            "VideoAssemblyService initialised",
            gpu_encoder=_GPU_ENCODER,
            chunk_count=self.CHUNK_COUNT,
        )

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
        parallel: bool = True,
    ) -> Dict:
        """
        Full video assembly pipeline with optional chunked parallel rendering.

        When parallel=True and scenes >= MIN_SCENES_FOR_PARALLEL:
          1. Split scenes into CHUNK_COUNT groups
          2. Render each group concurrently (asyncio.gather)
          3. Concat rendered chunks via ffmpeg concat demuxer
          Fallback: if any chunk fails, re-render sequentially.

        Returns {video_url, duration_seconds, size_bytes, render_mode}.
        """
        job_id = video_project_id or f"render_{int(asyncio.get_event_loop().time())}"
        work_dir = self.tmp_dir / job_id
        work_dir.mkdir(exist_ok=True)

        render_profile = PROFILES.get(profile, PROFILES["youtube_1080p"])
        # Swap in GPU encoder if available
        if _GPU_ENCODER != "libx264":
            render_profile = {**render_profile, "video_codec": _GPU_ENCODER, "crf": "0", "preset": "p4"}

        logger.info(
            "Video assembly started",
            job_id=job_id,
            profile=profile,
            gpu=_GPU_ENCODER,
            parallel=parallel,
        )

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

            # 4. Render: parallel chunks or sequential fallback
            output_path = work_dir / f"output_{job_id}.mp4"
            render_mode = "sequential"

            if parallel and len(scene_videos) >= self.MIN_SCENES_FOR_PARALLEL:
                try:
                    await self._render_parallel(
                        voice_path=str(voice_path),
                        scene_videos=scene_videos,
                        output_path=str(output_path),
                        captions_srt=captions_srt,
                        music_url=music_url,
                        work_dir=work_dir,
                        profile=render_profile,
                    )
                    render_mode = "parallel"
                except Exception as chunk_err:
                    logger.warning(
                        "Parallel render failed, falling back to sequential",
                        error=str(chunk_err),
                    )
                    await self._render_video(
                        voice_path=str(voice_path),
                        scene_videos=scene_videos,
                        output_path=str(output_path),
                        captions_srt=captions_srt,
                        music_url=music_url,
                        work_dir=work_dir,
                        profile=render_profile,
                    )
            else:
                await self._render_video(
                    voice_path=str(voice_path),
                    scene_videos=scene_videos,
                    output_path=str(output_path),
                    captions_srt=captions_srt,
                    music_url=music_url,
                    work_dir=work_dir,
                    profile=render_profile,
                )

            # 5. Upload to R2
            key = f"videos/{video_project_id or 'standalone'}/final.mp4"
            video_url = await storage_service.upload_file(str(output_path), key, "video/mp4")

            # 6. Final metadata
            final_duration = await self._get_video_duration(str(output_path))
            size_bytes = output_path.stat().st_size

            logger.info(
                "Video assembly complete",
                job_id=job_id,
                duration=final_duration,
                size_mb=round(size_bytes / 1024 / 1024, 1),
                render_mode=render_mode,
                url=video_url,
            )

            return {
                "video_url": video_url,
                "duration_seconds": final_duration,
                "size_bytes": size_bytes,
                "profile": profile,
                "render_mode": render_mode,
                "gpu_encoder": _GPU_ENCODER,
            }

        except Exception as e:
            logger.error("Video assembly failed", job_id=job_id, error=str(e))
            raise
        finally:
            import shutil
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

    # ── Parallel (Map-Reduce) Rendering ──────────────────────────────────────

    async def _render_parallel(
        self,
        voice_path: str,
        scene_videos: List[Dict],
        output_path: str,
        captions_srt: Optional[str],
        music_url: Optional[str],
        work_dir: Path,
        profile: Dict,
    ) -> None:
        """
        Map step: split scenes into CHUNK_COUNT groups, render each in parallel.
        Reduce step: concat rendered chunks with ffmpeg concat demuxer.
        """
        n_chunks = min(self.CHUNK_COUNT, len(scene_videos))
        chunk_size = math.ceil(len(scene_videos) / n_chunks)
        chunks = [
            scene_videos[i: i + chunk_size]
            for i in range(0, len(scene_videos), chunk_size)
        ]

        logger.info(
            "Parallel render: map phase",
            n_chunks=len(chunks),
            scenes_per_chunk=chunk_size,
        )

        # ── Map: render each chunk to its own temp file ───────────────────────
        chunk_paths: List[str] = []
        chunk_tasks = []

        for chunk_idx, chunk_scenes in enumerate(chunks):
            chunk_out = str(work_dir / f"chunk_{chunk_idx:03d}.mp4")
            chunk_paths.append(chunk_out)

            # Each chunk gets a silent voice (we mix audio at concat step)
            chunk_tasks.append(
                self._render_chunk(
                    chunk_scenes=chunk_scenes,
                    chunk_index=chunk_idx,
                    output_path=chunk_out,
                    work_dir=work_dir,
                    profile=profile,
                )
            )

        # Run all chunks concurrently
        await asyncio.gather(*chunk_tasks)

        # ── Reduce: concat all chunks + add audio in one pass ─────────────────
        await self._concat_chunks(
            chunk_paths=chunk_paths,
            voice_path=voice_path,
            music_url=music_url,
            captions_srt=captions_srt,
            output_path=output_path,
            work_dir=work_dir,
            profile=profile,
        )

    async def _render_chunk(
        self,
        chunk_scenes: List[Dict],
        chunk_index: int,
        output_path: str,
        work_dir: Path,
        profile: Dict,
    ) -> None:
        """
        Render a single chunk of scenes to a muted MP4 (no audio).
        Audio is mixed at the concat step to avoid desync.
        """
        inputs = []
        filter_parts = []
        concat_parts = []

        for i, scene in enumerate(chunk_scenes):
            if scene["path"] and os.path.exists(scene["path"]):
                if scene["type"] == "image":
                    inputs.extend([
                        "-loop", "1",
                        "-t", str(scene["duration"]),
                        "-i", scene["path"],
                    ])
                else:
                    inputs.extend(["-i", scene["path"]])
                filter_parts.append(
                    f"[{i}:v]scale={profile['resolution']},setsar=1,fps={profile['fps']}[v{i}]"
                )
            else:
                filter_parts.append(
                    f"color=black:s={profile['resolution']}:r={profile['fps']}:d={scene['duration']}[v{i}]"
                )
            concat_parts.append(f"[v{i}]")

        n = len(chunk_scenes)
        filter_complex = (
            ";".join(filter_parts)
            + f";{''.join(concat_parts)}concat=n={n}:v=1:a=0[vout]"
        )

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-an",                              # No audio in chunk
            "-c:v", profile["video_codec"],
            "-crf", str(profile["crf"]),
            "-preset", profile["preset"],
            "-pix_fmt", "yuv420p",
            output_path,
        ]

        logger.debug("Rendering chunk", chunk=chunk_index, scenes=n)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(
                f"Chunk {chunk_index} render failed: {stderr.decode()[-300:]}"
            )

    async def _concat_chunks(
        self,
        chunk_paths: List[str],
        voice_path: str,
        music_url: Optional[str],
        captions_srt: Optional[str],
        output_path: str,
        work_dir: Path,
        profile: Dict,
    ) -> None:
        """
        Reduce step: concatenate chunk MP4s using concat demuxer, then mix audio.
        Using concat demuxer (not filter) avoids re-encoding video — much faster.
        """
        # Write concat list file
        concat_list = work_dir / "concat_list.txt"
        concat_list.write_text(
            "\n".join(f"file '{p}'" for p in chunk_paths),
            encoding="utf-8",
        )

        # First pass: concat video chunks (copy codec — no re-encode)
        concat_video = str(work_dir / "concat_video.mp4")
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            concat_video,
        ]
        proc = await asyncio.create_subprocess_exec(
            *concat_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(f"Concat failed: {stderr.decode()[-300:]}")

        # Second pass: add voice + music + captions on top of concat_video
        await self._render_video(
            voice_path=voice_path,
            scene_videos=[],            # scenes already rendered — skip
            output_path=output_path,
            captions_srt=captions_srt,
            music_url=music_url,
            work_dir=work_dir,
            profile=profile,
            prerendered_video=concat_video,   # Use already-rendered video
        )

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
        prerendered_video: Optional[str] = None,
    ):
        """
        Build FFmpeg command and execute.

        If prerendered_video is provided (from parallel chunk concat), skip
        scene rendering and only mix audio + captions onto that video.
        """
        if prerendered_video:
            # Audio-only pass: overlay voice + music on pre-rendered video
            await self._mix_audio_onto_video(
                prerendered_video=prerendered_video,
                voice_path=voice_path,
                music_url=music_url,
                captions_srt=captions_srt,
                output_path=output_path,
                work_dir=work_dir,
                profile=profile,
            )
            return

        # ── Full sequential render (original path) ────────────────────────────
        inputs = ["-i", voice_path]
        filter_parts = []
        concat_parts = []

        for i, scene in enumerate(scene_videos):
            if scene["path"] and os.path.exists(scene["path"]):
                if scene["type"] == "image":
                    inputs.extend([
                        "-loop", "1",
                        "-t", str(scene["duration"]),
                        "-i", scene["path"],
                    ])
                else:
                    inputs.extend(["-i", scene["path"]])

                filter_parts.append(
                    f"[{i + 1}:v]scale={profile['resolution']},setsar=1[v{i}]"
                )
                concat_parts.append(f"[v{i}]")
            else:
                filter_parts.append(
                    f"color=black:s={profile['resolution']}:d={scene['duration']}[v{i}]"
                )
                concat_parts.append(f"[v{i}]")

        n_scenes = len(scene_videos)
        filter_complex = ";".join(filter_parts)
        filter_complex += f";{''.join(concat_parts)}concat=n={n_scenes}:v=1:a=0[vout]"

        audio_filter = "[0:a]"
        if music_url:
            music_path = work_dir / "music.mp3"
            await self._download_asset(music_url, music_path)
            inputs.extend(["-i", str(music_path)])
            music_idx = n_scenes + 1
            filter_complex += (
                f";[0:a]volume=1.0[voice];[{music_idx}:a]volume=0.12[music]"
                f";[voice][music]amix=inputs=2:duration=first[aout]"
            )
            audio_filter = "[aout]"

        if captions_srt:
            srt_path = work_dir / "captions.srt"
            srt_path.write_text(captions_srt, encoding="utf-8")
            filter_complex += (
                f";[vout]subtitles={srt_path}:force_style="
                f"'FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Bold=1,Outline=2'[vfinal]"
            )
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
            "-crf", str(profile["crf"]),
            "-preset", profile["preset"],
            "-c:a", profile["audio_codec"],
            "-b:a", profile["audio_bitrate"],
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            output_path,
        ]

        logger.debug("FFmpeg command (sequential)", cmd=" ".join(cmd[:10]) + "...")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise Exception(f"FFmpeg failed: {stderr.decode()[-500:]}")

    async def _mix_audio_onto_video(
        self,
        prerendered_video: str,
        voice_path: str,
        music_url: Optional[str],
        captions_srt: Optional[str],
        output_path: str,
        work_dir: Path,
        profile: Dict,
    ) -> None:
        """
        Overlay voice + optional music onto an already-rendered muted video.
        Used as the Reduce step after parallel chunk rendering.
        """
        inputs = ["-i", prerendered_video, "-i", voice_path]
        filter_parts = ["[0:v]copy[vout]"]

        audio_filter = "[1:a]"
        if music_url:
            music_path = work_dir / "music.mp3"
            if not music_path.exists():
                await self._download_asset(music_url, music_path)
            inputs.extend(["-i", str(music_path)])
            filter_parts.append(
                "[1:a]volume=1.0[voice];[2:a]volume=0.12[music]"
                ";[voice][music]amix=inputs=2:duration=first[aout]"
            )
            audio_filter = "[aout]"

        if captions_srt:
            srt_path = work_dir / "captions.srt"
            if not srt_path.exists():
                srt_path.write_text(captions_srt, encoding="utf-8")
            filter_parts[0] = (
                f"[0:v]subtitles={srt_path}:force_style="
                f"'FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                f"Bold=1,Outline=2'[vout]"
            )

        filter_complex = ";".join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", audio_filter,
            "-c:v", "copy",             # Re-encode only if captions added
            "-c:a", profile["audio_codec"],
            "-b:a", profile["audio_bitrate"],
            "-movflags", "+faststart",
            output_path,
        ]

        # If captions need burn-in, we must re-encode video
        if captions_srt:
            cmd[cmd.index("copy")] = profile["video_codec"]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(f"Audio mix failed: {stderr.decode()[-300:]}")

    async def generate_captions(self, voice_track_url: str, video_project_id: str = None) -> str:
        """
        Generate SRT captions using Whisper API.
        Returns SRT string.
        """
        import httpx
        from core.config import settings as _settings

        voice_path = self.tmp_dir / "caption_audio.mp3"
        await self._download_asset(voice_track_url, voice_path)

        trace = create_trace(
            name="whisper_transcription",
            input_data={"audio_url": voice_track_url, "language": "pl"},
            session_id=video_project_id,
            tags=["whisper", "captions"],
        )

        async with httpx.AsyncClient() as client:
            with open(voice_path, "rb") as f:
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {_settings.openai_api_key}"},
                    data={"model": "whisper-1", "response_format": "srt", "language": "pl"},
                    files={"file": ("audio.mp3", f, "audio/mpeg")},
                    timeout=120.0,
                )

        if response.status_code == 200:
            srt = response.text
            if trace:
                trace.update(output={"srt_length": len(srt)})
            return srt

        if trace:
            trace.update(output={"error": f"HTTP {response.status_code}"})
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
