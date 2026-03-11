"""
Agent #12: Audio Polish Agent — Layer 3 (Production)

Optimizes audio production: voice-over settings, background music selection,
audio levels, EQ recommendations, and LUFS normalization.

Also validates TTS output quality and selects optimal ElevenLabs voice settings.
Quality Gate: Audio quality score >= 80/100.
"""
import json
import time
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


AUDIO_POLISH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a professional audio engineer specializing in YouTube content production.

AUDIO STANDARDS FOR YOUTUBE 2026:
- Loudness: -14 LUFS integrated (YouTube normalization target)
- Peak: -1 dBTP (true peak) to prevent clipping
- Noise floor: < -60 dBFS
- Voice clarity: 1kHz-4kHz presence boost, reduce 300-500Hz muddy range
- Background music: -18 to -20 dBFS under voice (12-16 dB ducking)

ELEVENLABS VOICE OPTIMIZATION:
- stability: 0.5-0.7 (higher = more consistent but less expressive)
- similarity_boost: 0.7-0.9 (how closely to follow the cloned voice)
- style: 0.3-0.7 (style exaggeration — higher for emotional content)
- use_speaker_boost: true for professional narration
- model: eleven_multilingual_v2 for Polish, eleven_turbo_v2_5 for speed

VOICE RECOMMENDATIONS BY CONTENT TYPE:
- Educational/Tutorial: stability=0.65, similarity_boost=0.82, style=0.35
- Entertainment: stability=0.45, similarity_boost=0.78, style=0.65
- News/Informational: stability=0.75, similarity_boost=0.85, style=0.2
- Motivational: stability=0.5, similarity_boost=0.8, style=0.7

MUSIC SELECTION CRITERIA:
- Tempo: Match content pacing (60-80 BPM = calm, 100-130 = energetic)
- Genre: Lo-fi for education, cinematic for storytelling, upbeat for lifestyle
- Avoid: Songs with vocals that compete with narration
- Sources: YouTube Audio Library, Epidemic Sound, Artlist

RESPOND AS JSON:
{{
  "voice_settings": {{
    "stability": 0.65,
    "similarity_boost": 0.82,
    "style": 0.35,
    "use_speaker_boost": true,
    "model_id": "eleven_multilingual_v2"
  }},
  "audio_levels": {{
    "voice_lufs_target": -14,
    "music_db_under_voice": -16,
    "intro_music_fade_duration_s": 2.5,
    "outro_music_fade_in_s": 1.5
  }},
  "eq_recommendations": {{
    "voice_boost_hz": [2000, 4000],
    "voice_cut_hz": [300, 400],
    "music_high_shelf_cut_hz": 8000,
    "music_low_cut_hz": 200
  }},
  "music_recommendations": [
    {{
      "name": "Upbeat Acoustic",
      "source": "youtube_audio_library",
      "tempo_bpm": 95,
      "mood": "positive",
      "usage": "background throughout"
    }}
  ],
  "audio_quality_score": 85,
  "quality_gate_passed": true,
  "issues_found": [],
  "improvements": ["..."]
}}"""),
    ("human", """Script text: {script_excerpt}
Video format: {format}
Niche: {niche}
Tone: {tone}
Language: {language}
Current voice settings: {current_settings}
Duration estimate (seconds): {duration}"""),
])


class AudioPolishAgent(BaseAgent):
    agent_id = "audio_polish"
    layer = 3
    description = "Voice settings optimization, audio levels, music selection, LUFS normalization"
    tools = ["ElevenLabs settings optimizer", "Audio level calculator", "Music recommender", "EQ analyzer"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("analyze_audio_needs", self._analyze_audio_needs)
        workflow.add_node("validate_tts_output", self._validate_tts_output)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "analyze_audio_needs")
        workflow.add_edge("analyze_audio_needs", "validate_tts_output")
        workflow.add_edge("validate_tts_output", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _analyze_audio_needs(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        chain = AUDIO_POLISH_PROMPT | self.llm_fast

        script_text = input_data.get("script_text", "")
        word_count = len(script_text.split())
        duration_est = int(word_count / 130 * 60)

        response = await chain.ainvoke({
            "script_excerpt": script_text[:1000],
            "format": input_data.get("format", "educational"),
            "niche": input_data.get("niche", ""),
            "tone": input_data.get("tone", "professional"),
            "language": input_data.get("language", "Polish"),
            "current_settings": json.dumps(input_data.get("current_voice_settings", {})),
            "duration": duration_est,
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            audio_config = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            audio_config = {
                "voice_settings": {
                    "stability": 0.65,
                    "similarity_boost": 0.82,
                    "style": 0.35,
                    "use_speaker_boost": True,
                    "model_id": "eleven_multilingual_v2",
                },
                "audio_quality_score": 75,
                "quality_gate_passed": True,
                "error": "Parse failed — using defaults",
            }

        state["output_data"]["audio_config"] = audio_config
        return state

    async def _validate_tts_output(self, state: AgentState) -> AgentState:
        """If TTS audio URL provided, validate it exists and is accessible."""
        input_data = state["input_data"]
        audio_url = input_data.get("tts_audio_url")

        if audio_url:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.head(audio_url, timeout=5.0)
                    state["output_data"]["tts_validation"] = {
                        "url": audio_url,
                        "accessible": resp.status_code == 200,
                        "content_type": resp.headers.get("content-type", ""),
                    }
            except Exception as e:
                state["output_data"]["tts_validation"] = {"url": audio_url, "accessible": False, "error": str(e)}
        else:
            state["output_data"]["tts_validation"] = {"url": None, "accessible": None, "note": "No TTS URL provided"}

        return state

    async def _finalize(self, state: AgentState) -> AgentState:
        audio_config = state["output_data"].get("audio_config", {})
        quality_score = audio_config.get("audio_quality_score", 75)
        gate_passed = quality_score >= 80

        state["output_data"]["final"] = {
            "voice_settings": audio_config.get("voice_settings", {}),
            "audio_levels": audio_config.get("audio_levels", {}),
            "eq_recommendations": audio_config.get("eq_recommendations", {}),
            "music_recommendations": audio_config.get("music_recommendations", []),
            "audio_quality_score": quality_score,
            "issues_found": audio_config.get("issues_found", []),
            "improvements": audio_config.get("improvements", []),
            "tts_validation": state["output_data"].get("tts_validation", {}),
            "quality_gate_passed": gate_passed,
            "quality_gate_threshold": 80,
            "message": (
                f"Audio gate PASSED: Quality {quality_score}/100"
                if gate_passed
                else f"Audio gate FAILED: Quality {quality_score}/100 < 80"
            ),
        }
        state["quality_scores"]["audio_quality"] = float(quality_score)
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


audio_polish_agent = AudioPolishAgent()
