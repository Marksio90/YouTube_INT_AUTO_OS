"""
Agent #9: Title Architect — Layer 3 (Production)

Generates and scores YouTube titles using CTR psychology, SEO,
and clickbait-without-disappointment principles.

Quality Gate: Title SEO score >= 75, CTR score >= 7/10.
Title formulas: How-to, listicle, question, number, secret, emotional.
"""
import json
import time
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


TITLE_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a YouTube title architect. You craft titles that rank AND get clicked.

TITLE SCIENCE (2026):
- Character limit: 60-70 chars for full display on mobile
- Front-load keywords: Most important word in first 3 words
- Number power: Odd numbers outperform even by 20% (7 > 6, 11 > 10)
- Brackets/parentheses: Add context without length penalty
- Year freshness: "(2026)" in title for evergreen topics boosts CTR
- Emotional words that work: Ultimate, Shocking, Secret, Never, Mistake, Truth, Exposed

TITLE FORMULAS (generate at least one of each):
1. HOW-TO: "How to [Outcome] [Without/Even If] [Objection]"
2. LISTICLE: "[Number] [Adjective] Ways to [Achieve Result]"
3. QUESTION: "Why [Common Belief] Is [Surprising Adjective]"
4. SECRET: "The [Secret/Hidden/Unknown] [Method/Trick] [Experts/Pro] Use"
5. BEFORE/AFTER: "I [Action] for [Time] — Here's What Happened"
6. MISTAKE: "[Number] [Topic] Mistakes That Are [Costing/Ruining/Killing] Your [Outcome]"
7. ULTIMATE: "The Ultimate Guide to [Topic] in [Year]"

SEO REQUIREMENTS:
- Primary keyword in first 5 words
- Natural language (not keyword stuffing)
- Search intent match (informational/navigational/transactional)
- Related keywords included naturally

RESPOND AS JSON:
{{
  "titles": [
    {{
      "formula": "how_to|listicle|question|secret|before_after|mistake|ultimate",
      "title": "Full title text",
      "character_count": 58,
      "primary_keyword_position": 2,
      "ctr_score": 8.2,
      "seo_score": 78,
      "emotional_words": ["Ultimate", "Secret"],
      "search_volume_estimate": "high|medium|low",
      "clickbait_risk": "none|low|medium|high",
      "explanation": "Why this works"
    }}
  ],
  "best_title_index": 0,
  "primary_keyword": "...",
  "recommended_hashtags": ["#tag1", "#tag2"],
  "ab_test_pair": [0, 1]
}}"""),
    ("human", """Script topic: {topic}
Target keyword: {keyword}
Niche: {niche}
Channel tone: {tone}
Script summary: {summary}
Generate {n_titles} title variants."""),
])


class TitleArchitectAgent(BaseAgent):
    agent_id = "title_architect"
    layer = 3
    description = "Generates SEO-optimized titles with CTR psychology. Gate: SEO>=75, CTR>=7/10"
    tools = ["Title formula library", "SEO scorer", "CTR predictor", "Keyword density checker"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("generate_titles", self._generate_titles)
        workflow.add_node("evaluate_titles", self._evaluate_titles)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "generate_titles")
        workflow.add_edge("generate_titles", "evaluate_titles")
        workflow.add_edge("evaluate_titles", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _generate_titles(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        chain = TITLE_GENERATION_PROMPT | self.llm_premium

        response = await chain.ainvoke({
            "topic": input_data.get("topic", input_data.get("title", "")),
            "keyword": input_data.get("target_keyword", input_data.get("niche", "")),
            "niche": input_data.get("niche", ""),
            "tone": input_data.get("tone", "educational"),
            "summary": input_data.get("script_text", "")[:500],
            "n_titles": input_data.get("n_titles", 7),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            titles_data = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            titles_data = {"titles": [], "error": "Parse failed"}

        state["output_data"]["titles_raw"] = titles_data
        return state

    async def _evaluate_titles(self, state: AgentState) -> AgentState:
        """Filter out high clickbait risk titles, rank the rest."""
        titles_data = state["output_data"].get("titles_raw", {})
        titles = titles_data.get("titles", [])

        # Filter high clickbait risk
        safe_titles = [t for t in titles if t.get("clickbait_risk") != "high"]
        if not safe_titles:
            safe_titles = titles  # fallback: keep all if all flagged

        state["output_data"]["titles_evaluated"] = safe_titles
        return state

    async def _finalize(self, state: AgentState) -> AgentState:
        titles_raw = state["output_data"].get("titles_raw", {})
        titles = state["output_data"].get("titles_evaluated", [])

        if not titles:
            state["output_data"]["final"] = {
                "best_title": None,
                "all_titles": [],
                "quality_gate_passed": False,
            }
            return state

        best_index = titles_raw.get("best_title_index", 0)
        # Ensure index is within safe_titles bounds
        if best_index >= len(titles):
            best_index = 0

        best = titles[best_index]
        best_seo = best.get("seo_score", 0)
        best_ctr = best.get("ctr_score", 0)
        gate_passed = best_seo >= 75 and best_ctr >= 7.0

        state["output_data"]["final"] = {
            "best_title": best["title"],
            "best_title_data": best,
            "all_titles": titles,
            "primary_keyword": titles_raw.get("primary_keyword", ""),
            "recommended_hashtags": titles_raw.get("recommended_hashtags", []),
            "ab_test_pair": titles_raw.get("ab_test_pair", [0, 1]),
            "best_seo_score": best_seo,
            "best_ctr_score": best_ctr,
            "quality_gate_passed": gate_passed,
            "quality_gate_threshold": {"seo": 75, "ctr": 7.0},
            "message": (
                f"Title gate PASSED: SEO {best_seo}/100, CTR {best_ctr:.1f}/10 — '{best['title'][:50]}'"
                if gate_passed
                else f"Title gate FAILED: SEO {best_seo}/100 < 75 or CTR {best_ctr:.1f}/10 < 7"
            ),
        }
        state["quality_scores"]["title_seo_score"] = float(best_seo)
        state["quality_scores"]["title_ctr_score"] = best_ctr
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


title_architect_agent = TitleArchitectAgent()
