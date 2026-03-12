"""
Agent #6: Voice Persona — Layer 2 (Content Design Engine)

Defines and maintains a consistent voice and tone for a channel's content.
Analyzes existing content to extract voice patterns and generates a persona
guide that other agents (Script Strategist, Hook Specialist) use to stay on-brand.

Quality Gate: Voice-Brand Fit >= 8/10, Consistency Score >= 8/10
"""
import json
import time
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState
from core.config import settings

VOICE_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert YouTube brand voice analyst.
Your task: analyze a channel's content and extract its unique voice persona.

ANALYZE THESE DIMENSIONS:
1. Tone Spectrum: Where on these scales?
   - Formal ←→ Casual
   - Serious ←→ Humorous
   - Academic ←→ Street-smart
   - Empathetic ←→ Provocative
2. Vocabulary Profile: Technical jargon level, slang usage, signature phrases
3. Sentence Patterns: Short punchy vs flowing narrative, question frequency
4. Emotional Register: Primary emotions evoked (curiosity, urgency, empowerment)
5. Cultural References: What world does this creator live in?
6. Forbidden Patterns: AI-smell phrases to NEVER use ("delve", "game-changer", "in today's video")
7. Signature Moves: Unique verbal tics, catchphrases, opening/closing rituals

RESPOND AS JSON:
{{
  "persona_name": "Short memorable name for this voice",
  "one_liner": "One sentence describing this voice",
  "tone_profile": {{
    "formality": 1-10,
    "humor": 1-10,
    "technical_depth": 1-10,
    "empathy": 1-10,
    "provocation": 1-10,
    "energy": 1-10
  }},
  "vocabulary": {{
    "reading_level": "middle_school|high_school|college|expert",
    "jargon_density": "none|light|moderate|heavy",
    "signature_phrases": ["phrase1", "phrase2"],
    "power_words": ["word1", "word2"],
    "forbidden_words": ["word1", "word2"]
  }},
  "sentence_patterns": {{
    "avg_length": "short|medium|long",
    "question_frequency": "rare|occasional|frequent",
    "rhetorical_devices": ["device1", "device2"]
  }},
  "emotional_register": {{
    "primary_emotion": "curiosity|urgency|empowerment|fear|inspiration",
    "secondary_emotion": "...",
    "emotional_arc": "build_up|steady|roller_coaster"
  }},
  "brand_rules": [
    "Always do X",
    "Never do Y"
  ],
  "example_hooks": ["Hook in this voice style 1", "Hook in this voice style 2"],
  "consistency_score": 8.5,
  "voice_brand_fit": 8.5,
  "quality_gate_passed": true
}}"""),
    ("human", """Channel: {channel_name}
Niche: {niche}
Channel description: {channel_description}
Content pillars: {content_pillars}
Target audience: {target_audience}
Existing content samples:
{content_samples}
Language: {language}"""),
])

VOICE_CONSISTENCY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a voice consistency checker.
Given a voice persona guide and a text sample, score how well the text
matches the defined voice on a 0-10 scale.

Check:
1. Does it use the right tone (formality, humor, energy)?
2. Does it avoid forbidden words/patterns?
3. Does it use signature phrases naturally?
4. Does the emotional register match?
5. Does sentence structure match the pattern?

RESPOND AS JSON:
{{
  "consistency_score": 8.5,
  "matches": ["What aligns with the persona"],
  "violations": ["What breaks the persona"],
  "suggestions": ["How to fix violations"]
}}"""),
    ("human", """Voice Persona:
{persona_json}

Text to check:
{text_sample}"""),
])


class VoicePersonaAgent(BaseAgent):
    agent_id = "voice_persona"
    layer = 2
    description = "Defines and maintains consistent voice and tone across all channel content"
    tools = ["Channel content analysis", "Voice consistency checker", "Brand guidelines"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("analyze_voice", self._analyze_voice)
        workflow.add_node("validate_persona", self._validate_persona)
        workflow.add_node("quality_gate", self._quality_gate)

        workflow.add_edge(START, "analyze_voice")
        workflow.add_edge("analyze_voice", "validate_persona")
        workflow.add_edge("validate_persona", "quality_gate")

        workflow.add_conditional_edges(
            "quality_gate",
            self._should_retry,
            {"retry": "analyze_voice", "done": END},
        )

        return workflow.compile(checkpointer=self._checkpointer)

    async def _analyze_voice(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]

        # MACRO tier — complex multi-dimensional analysis
        llm = self.get_routed_llm("channel_strategy", context_length=3000)
        chain = VOICE_ANALYSIS_PROMPT | llm

        content_samples = input_data.get("content_samples", [])
        samples_text = "\n---\n".join(
            [s[:500] for s in content_samples[:5]]
        ) if content_samples else "No existing content samples available — create a fresh persona."

        response = await chain.ainvoke({
            "channel_name": input_data.get("channel_name", ""),
            "niche": input_data.get("niche", ""),
            "channel_description": input_data.get("channel_description", ""),
            "content_pillars": ", ".join(input_data.get("content_pillars", [])),
            "target_audience": input_data.get("target_audience", "general YouTube viewers"),
            "content_samples": samples_text,
            "language": input_data.get("language", "en"),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            persona = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            persona = {"error": "Parse failed", "raw": response.content[:500]}

        state["output_data"]["persona"] = persona
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        return state

    async def _validate_persona(self, state: AgentState) -> AgentState:
        """Validate persona by checking example hooks against it."""
        persona = state["output_data"].get("persona", {})

        if "error" in persona:
            state["quality_scores"]["consistency_score"] = 0
            return state

        example_hooks = persona.get("example_hooks", [])
        if not example_hooks:
            state["quality_scores"]["consistency_score"] = persona.get("consistency_score", 7.0)
            return state

        # MICRO tier — simple consistency scoring
        scorer_llm = self.get_routed_llm("score_hook")
        chain = VOICE_CONSISTENCY_PROMPT | scorer_llm

        try:
            resp = await chain.ainvoke({
                "persona_json": json.dumps(persona, ensure_ascii=False)[:2000],
                "text_sample": example_hooks[0],
            })
            content = resp.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            validation = json.loads(content.strip())
            score = validation.get("consistency_score", 7.0)
        except Exception:
            score = 7.0
            validation = {}

        state["quality_scores"]["consistency_score"] = score
        state["output_data"]["validation"] = validation
        return state

    async def _quality_gate(self, state: AgentState) -> AgentState:
        persona = state["output_data"].get("persona", {})
        consistency = state["quality_scores"].get("consistency_score", 0)
        voice_fit = float(persona.get("voice_brand_fit", 0))

        gate_passed = consistency >= 8.0 and voice_fit >= 8.0

        state["output_data"]["quality_gate"] = {
            "passed": gate_passed,
            "consistency_score": consistency,
            "voice_brand_fit": voice_fit,
            "thresholds": {"consistency_score": 8.0, "voice_brand_fit": 8.0},
        }
        state["quality_scores"]["voice_brand_fit"] = voice_fit
        return state

    def _should_retry(self, state: AgentState) -> str:
        gate = state["output_data"].get("quality_gate", {})
        if not gate.get("passed") and state.get("iteration_count", 0) < 2:
            return "retry"
        return "done"

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        run_id = f"{self.agent_id}-{time.time()}"
        config = {"configurable": {"thread_id": run_id}}
        final_state = await graph.ainvoke(self._initial_state(input_data, run_id=run_id), config)
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


voice_persona_agent = VoicePersonaAgent()
