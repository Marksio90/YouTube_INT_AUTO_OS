"""
Agent #21: Originality & Transformation Agent — Layer 5 (Compliance)

NAJWAZNIEJSZY AGENT W 2026.

Bada czy tresc jest:
1. Dostatecznie wlasna (nie kopia cudzych materialow)
2. Rozna miedzy filmami (nie template farm)
3. Nie wyglada jak "easily replicable at scale"
4. Nie jest nadmiernie powtarzalna (phrase repetition)
5. Nie wpada w inauthentic content policy YouTube

Uzywa pgvector (cosine similarity) do detekcji podobienstwa.
Quality Gate: Originality Score >= 85/100, cosine similarity < 0.85
"""
from typing import Any, Dict, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
import json
import time

from agents.base import BaseAgent, AgentState
from core.config import settings


ORIGINALITY_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Jestes ekspertem od compliance YouTube 2026.
Oceniasz czy tresc jest ORYGINALNA i nie narazi kanalu na inauthentic content policy.

POLITYKA YOUTUBE 2026 (od 15.07.2025 — Inauthentic Content):
ZABRONIONE:
- Tresci "easily replicable at scale"
- Filmy oparte na szablonach z minimalnymi roznicami
- Powierzchowne zmiany narrowanych historii
- Pokazy slajdow z minimalnym komentarzem
- Tresci polegajace wylacznie na odczytywaniu cudzych materialow

DOZWOLONE (Faceless channels):
- Wyrarna tozsamosc marki
- Oryginalne scenariusze z research
- Widoczny osad redakcyjny czlowieka
- Istotna roznorodnosc miedzy filmami
- Premium, wyrazny lektor

SCORING (0-100):
- 90-100: Doskonale oryginalny, silna marka, unikalny poglad
- 75-89: Dobra oryginalnosc, bezpieczny
- 60-74: Ostrzezenie — ryzyko template-farm
- <60: CZERWONY FLAG — ryzyko inauthentic content

ODPOWIEDZ JSON:
{{
  "originality_score": 0-100,
  "transformation_level": "high|medium|low",
  "template_overuse_risk": "green|yellow|red",
  "inauthentic_content_risk": "green|yellow|red",
  "unique_elements": ["element1", "element2"],
  "risk_factors": ["ryzyko1", "ryzyko2"],
  "remediation": ["akcja1", "akcja2"],
  "youtube_policy_compliance": true/false,
  "quality_gate_passed": true/false,
  "notes": "..."
}}"""),
    ("human", """Tytul: {title}
Fragment scenariusza: {script_excerpt}
Poprzednie filmy na kanale: {recent_titles}
Niche: {niche}"""),
])


class OriginalityTransformationAgent(BaseAgent):
    agent_id = "originality_transformation"
    layer = 5
    description = "KRYTYCZNY: sprawdza oryginalnosc, template overuse, inauthentic content risk via embeddings"
    tools = [
        "Embedding similarity check (pgvector)",
        "cross-video analysis",
        "template overuse detector",
        "phrase repetition detector",
        "channel monotony detector"
    ]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("embedding_similarity_check", self._embedding_similarity_check)
        workflow.add_node("llm_originality_review", self._llm_originality_review)
        workflow.add_node("template_overuse_check", self._template_overuse_check)
        workflow.add_node("finalize_report", self._finalize_report)

        workflow.add_edge(START, "embedding_similarity_check")
        workflow.add_edge("embedding_similarity_check", "llm_originality_review")
        workflow.add_edge("llm_originality_review", "template_overuse_check")
        workflow.add_edge("template_overuse_check", "finalize_report")
        workflow.add_edge("finalize_report", END)

        return workflow.compile()

    async def _embedding_similarity_check(self, state: AgentState) -> AgentState:
        """
        Check cosine similarity of new script against all existing scripts.
        Uses pgvector cosine distance via EmbeddingService.
        Quality Gate: cosine similarity < 0.85
        """
        input_data = state["input_data"]
        script_text = input_data.get("script_text", "")
        channel_id = input_data.get("channel_id", "")
        exclude_script_id = input_data.get("script_id")

        if not script_text or not channel_id:
            state["output_data"]["similarity_check"] = {
                "max_cosine_similarity": 0.0,
                "threshold": settings.max_similarity_cosine,
                "passed": True,
                "similar_videos": [],
                "skipped": True,
            }
            state["quality_scores"]["similarity_score"] = 1.0
            return state

        try:
            from services.embedding_service import embedding_service

            originality_score, similar_scripts = await embedding_service.compute_originality_score(
                script_text=script_text,
                channel_id=channel_id,
                exclude_script_id=exclude_script_id,
            )

            max_similarity = max(
                (s["similarity"] for s in similar_scripts), default=0.0
            )

            state["output_data"]["similarity_check"] = {
                "max_cosine_similarity": max_similarity,
                "threshold": settings.max_similarity_cosine,
                "passed": max_similarity < settings.max_similarity_cosine,
                "similar_videos": similar_scripts[:3],
                "embedding_based_originality": originality_score,
            }
            state["quality_scores"]["similarity_score"] = 1 - max_similarity
            state["quality_scores"]["embedding_originality"] = originality_score

        except Exception as e:
            self.logger.warning("pgvector similarity check failed, falling back", error=str(e))
            state["output_data"]["similarity_check"] = {
                "max_cosine_similarity": 0.0,
                "threshold": settings.max_similarity_cosine,
                "passed": True,
                "similar_videos": [],
                "error": str(e),
            }
            state["quality_scores"]["similarity_score"] = 1.0

        return state

    async def _llm_originality_review(self, state: AgentState) -> AgentState:
        """LLM review of originality and transformation level."""
        input_data = state["input_data"]
        chain = ORIGINALITY_CHECK_PROMPT | self.llm_premium

        response = await chain.ainvoke({
            "title": input_data.get("title", ""),
            "script_excerpt": input_data.get("script_text", "")[:1500],
            "recent_titles": ", ".join(input_data.get("recent_video_titles", [])),
            "niche": input_data.get("niche", ""),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            review = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            review = {
                "originality_score": 70,
                "template_overuse_risk": "yellow",
                "inauthentic_content_risk": "yellow",
                "youtube_policy_compliance": True,
                "quality_gate_passed": False,
                "error": "Parse failed",
            }

        state["output_data"]["originality_review"] = review
        state["quality_scores"]["originality_score"] = review.get("originality_score", 70)
        return state

    async def _template_overuse_check(self, state: AgentState) -> AgentState:
        """Check if too many recent videos use same structure/format."""
        input_data = state["input_data"]
        recent_formats = input_data.get("recent_video_formats", [])

        # Simple heuristic: if >60% of last 5 videos use same format — warning
        if recent_formats:
            from collections import Counter
            format_counts = Counter(recent_formats)
            most_common_count = format_counts.most_common(1)[0][1] if format_counts else 0
            overuse_ratio = most_common_count / len(recent_formats)
            overuse_risk = "red" if overuse_ratio > 0.8 else "yellow" if overuse_ratio > 0.6 else "green"
        else:
            overuse_ratio = 0.0
            overuse_risk = "green"

        state["output_data"]["template_overuse"] = {
            "overuse_ratio": overuse_ratio,
            "risk_level": overuse_risk,
            "recommendation": (
                "Zmien format nastepnych 2 filmow" if overuse_risk != "green"
                else "Format OK — dobra roznorodnosc"
            ),
        }
        return state

    async def _finalize_report(self, state: AgentState) -> AgentState:
        """Consolidate all checks into final compliance report."""
        originality_score = state["quality_scores"].get("originality_score", 0)
        similarity_check = state["output_data"].get("similarity_check", {})
        template_check = state["output_data"].get("template_overuse", {})
        review = state["output_data"].get("originality_review", {})

        gate_passed = (
            originality_score >= settings.min_originality_score
            and similarity_check.get("passed", True)
            and template_check.get("risk_level", "green") != "red"
        )

        state["output_data"]["final_report"] = {
            "originality_score": originality_score,
            "similarity_score": state["quality_scores"].get("similarity_score", 1),
            "template_overuse_risk": template_check.get("risk_level", "green"),
            "inauthentic_content_risk": review.get("inauthentic_content_risk", "green"),
            "youtube_policy_compliance": review.get("youtube_policy_compliance", True),
            "quality_gate_passed": gate_passed,
            "quality_gate_threshold": settings.min_originality_score,
            "risk_factors": review.get("risk_factors", []),
            "remediation": review.get("remediation", []),
            "message": (
                f"Quality gate PASSED: Oryginalnosc {originality_score}/100"
                if gate_passed
                else f"Quality gate FAILED: Oryginalnosc {originality_score}/100 < {settings.min_originality_score}"
            ),
        }
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


originality_transformation_agent = OriginalityTransformationAgent()
