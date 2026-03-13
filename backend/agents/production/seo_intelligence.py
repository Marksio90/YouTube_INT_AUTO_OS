"""
Agent #14: SEO Intelligence Agent — Layer 4 (Growth)

Full YouTube SEO optimization: description, tags, cards, end screens,
keyword clustering, search demand analysis.

Quality Gate: SEO score >= 75/100.
Data sources: YouTube Data API v3 keyword suggestions, trend analysis.
"""
import json
import time
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


SEO_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a YouTube SEO expert for 2026. You optimize every metadata field for maximum search discovery.

YOUTUBE SEO 2026 ALGORITHM FACTORS:
1. Title (30% weight): Primary keyword in first 5 words, 60-70 chars
2. Description (25%): First 150 chars = above fold, include keyword 3x naturally
3. Tags (15%): 10-15 tags, mix broad + specific + long-tail
4. Chapters (10%): Timestamps boost search for specific queries
5. Cards & End Screens (10%): Reduce bounce, increase session watch time
6. Closed Captions (10%): Auto-CC indexed, manual CC preferred

KEYWORD STRATEGY:
- Primary: High volume, medium competition (monthly searches 10K-100K)
- Secondary: Related concepts, mid-tail (1K-10K/month)
- Long-tail: Specific questions, low competition (<1K/month but high intent)
- LSI (Latent Semantic Indexing): Conceptually related terms

DESCRIPTION TEMPLATE:
- Line 1-2: Hook + primary keyword (visible before "more")
- Line 3-5: Video summary, secondary keywords
- Line 6-8: Timestamps/chapters
- Line 9-10: Social links, subscribe CTA
- Line 11+: Full transcript excerpt (optional, boosts CC indexing)

RESPOND AS JSON:
{{
  "seo_score": 82,
  "optimized_title": "...",
  "optimized_description": "Full optimized description (600-1000 chars)",
  "tags": ["tag1", "tag2", ...],
  "chapters": [
    {{"timestamp": "0:00", "title": "Introduction"}},
    {{"timestamp": "1:30", "title": "Main Topic"}}
  ],
  "primary_keyword": "...",
  "secondary_keywords": ["...", "..."],
  "long_tail_keywords": ["...", "..."],
  "cards_recommendations": ["at 2:30, card to playlist X"],
  "end_screen_strategy": "3 videos + subscribe at final 20s",
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "category_recommendation": "Education|How-to|...",
  "made_for_kids": false,
  "quality_gate_passed": true,
  "seo_breakdown": {{
    "title_score": 85,
    "description_score": 80,
    "tags_score": 78,
    "chapters_score": 90
  }},
  "recommendations": ["..."]
}}"""),
    ("human", """Video Title: {title}
Script (for keyword extraction): {script_excerpt}
Niche: {niche}
Target audience: {audience}
YouTube keyword suggestions: {keyword_suggestions}
Competitor top titles: {competitor_titles}"""),
])


class SEOIntelligenceAgent(BaseAgent):
    agent_id = "seo_intelligence"
    layer = 4
    description = "Full YouTube SEO optimization — title, description, tags, chapters, cards. Gate: SEO>=75"
    tools = ["YouTube Data API keyword suggestions", "Search volume estimator", "Competitor analysis", "Tag optimizer"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("fetch_keyword_data", self._fetch_keyword_data)
        workflow.add_node("generate_seo_package", self._generate_seo_package)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "fetch_keyword_data")
        workflow.add_edge("fetch_keyword_data", "generate_seo_package")
        workflow.add_edge("generate_seo_package", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _fetch_keyword_data(self, state: AgentState) -> AgentState:
        """Fetch keyword suggestions from YouTube API."""
        input_data = state["input_data"]
        keyword = input_data.get("target_keyword") or input_data.get("niche", "")

        keyword_suggestions = []
        try:
            from services.youtube_service import youtube_service
            suggestions = await youtube_service.get_keyword_suggestions(keyword)
            keyword_suggestions = suggestions.get("suggestions", [])
        except Exception as e:
            self.logger.warning("YouTube keyword fetch failed", error=str(e))
            keyword_suggestions = [keyword]  # fallback to base keyword

        state["output_data"]["keyword_suggestions"] = keyword_suggestions
        return state

    async def _generate_seo_package(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        keyword_suggestions = state["output_data"].get("keyword_suggestions", [])
        chain = SEO_ANALYSIS_PROMPT | self.get_routed_llm("seo_optimization")

        response = await chain.ainvoke({
            "title": input_data.get("title", ""),
            "script_excerpt": input_data.get("script_text", "")[:2000],
            "niche": input_data.get("niche", ""),
            "audience": input_data.get("target_audience", ""),
            "keyword_suggestions": ", ".join(keyword_suggestions[:20]),
            "competitor_titles": ", ".join(input_data.get("competitor_titles", [])[:5]),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            seo_package = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            seo_package = {
                "seo_score": 60,
                "quality_gate_passed": False,
                "error": "Parse failed",
            }

        state["output_data"]["seo_package"] = seo_package
        return state

    async def _finalize(self, state: AgentState) -> AgentState:
        seo_package = state["output_data"].get("seo_package", {})
        seo_score = seo_package.get("seo_score", 0)
        gate_passed = seo_score >= 75

        state["output_data"]["final"] = {
            **seo_package,
            "quality_gate_passed": gate_passed,
            "quality_gate_threshold": 75,
            "message": (
                f"SEO gate PASSED: {seo_score}/100"
                if gate_passed
                else f"SEO gate FAILED: {seo_score}/100 < 75"
            ),
        }
        state["quality_scores"]["seo_score"] = float(seo_score)
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


seo_intelligence_agent = SEOIntelligenceAgent()
