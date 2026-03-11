"""
Agent #4: Channel Architect Agent — Layer 2 (Content Design Engine)

Projektuje caly kanal:
- Pozycjonowanie i obietnica kanalu
- 3-5 filarow tresci
- Styl miniatur (template DNA, nie identyczny)
- Ton lektora i voice persona
- Format intro/CTA
- Biblioteka serii
- Brand consistency rules

Output: Channel Blueprint — kompletny dokument strategii kanalu
"""
from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
import json
import time

from agents.base import BaseAgent, AgentState


CHANNEL_ARCHITECT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Jestes architektem marek medialnych na YouTube. 2026 rok.
Projektujesz kanaly ktore sa ORYGINALNE, ZGODNE z politykami i WYSOKO-KONWERTUJACE.

ZASADY (KRYTYCZNE):
1. Kanal musi miec wyrazna TOZSAMOSC — nie moze wygladac jak template farm
2. Miniatury maja miec wspolny DNA (styl, kolory) ale NIE byc identyczne
3. Voice persona musi byc unikalna dla kanalu
4. Filary tresci = 3-5 kategorii ktore buduja authority i wracajacych widzow
5. Kazda seria musi miec unikalna wartosc — nie duplication

ODPOWIEDZ JSON — kompletny Channel Blueprint:
{{
  "channel_name": "...",
  "channel_promise": "Jedna zdanie: co widz zyska subskrybujac?",
  "target_audience": {{
    "primary": "...",
    "secondary": "...",
    "pain_points": ["bol1", "bol2"],
    "aspirations": ["cel1", "cel2"]
  }},
  "positioning": "Unikalne pozycjonowanie vs konkurencja",
  "content_pillars": [
    {{"name": "Filar 1", "description": "...", "video_types": ["typ1", "typ2"], "frequency": "2x miesiecznie"}}
  ],
  "voice_persona": {{
    "name": "Persona Name",
    "tone": "authoritative|friendly|educational|entertaining",
    "energy": "high|medium|low",
    "warmth": "high|medium|low",
    "key_phrases": ["fraza1", "fraza2"],
    "avoid": ["unikaj1", "unikaj2"]
  }},
  "visual_identity": {{
    "thumbnail_style": "Opis stylu miniatur",
    "color_palette": ["#kolor1", "#kolor2", "#kolor3"],
    "thumbnail_text_policy": "Maks 4 slowa, duzy kontrast",
    "face_vs_graphic": "graphic|face|mixed"
  }},
  "intro_format": {{
    "duration_seconds": 0,
    "structure": "Hook -> Obietnica -> Proof",
    "recurring_elements": ["element1"]
  }},
  "cta_format": {{
    "primary_cta": "...",
    "timing": "ostatnie 30-45 sekund",
    "subscription_pitch": "..."
  }},
  "series_library": [
    {{"name": "Seria 1", "format": "...", "episode_count": "ongoing|limited", "cadence": "weekly"}}
  ],
  "brand_rules": ["regula1", "regula2", "regula3"],
  "monetization_strategy": {{
    "primary": "adsense|affiliate|sponsorship|digital_products",
    "secondary": ["...", "..."],
    "rpm_target": 0.0
  }}
}}"""),
    ("human", """Nisza: {niche_name}
Analiza niszy: {niche_analysis}
Analiza konkurencji: {competitive_analysis}
Jezyk: {language}
Dodatkowe wymagania: {requirements}"""),
])


class ChannelArchitectAgent(BaseAgent):
    agent_id = "channel_architect"
    layer = 2
    description = "Projektuje caly kanal: pozycjonowanie, filary tresci, voice persona, styl miniatur, intro DNA"
    tools = ["Competitive Deconstruction output", "niche data", "brand style templates", "audience persona data"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("design_channel", self._design_channel)
        workflow.add_node("validate_blueprint", self._validate_blueprint)
        workflow.add_edge(START, "design_channel")
        workflow.add_edge("design_channel", "validate_blueprint")
        workflow.add_edge("validate_blueprint", END)
        return workflow.compile()

    async def _design_channel(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        chain = CHANNEL_ARCHITECT_PROMPT | self.llm_premium

        response = await chain.ainvoke({
            "niche_name": input_data.get("niche_name", ""),
            "niche_analysis": json.dumps(input_data.get("niche_analysis", {}), ensure_ascii=False)[:2000],
            "competitive_analysis": json.dumps(input_data.get("competitive_analysis", {}), ensure_ascii=False)[:2000],
            "language": input_data.get("language", "pl"),
            "requirements": input_data.get("requirements", "Brak specjalnych wymagan"),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            blueprint = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            blueprint = {"error": "Parse failed", "raw": response.content[:500]}

        state["output_data"]["channel_blueprint"] = blueprint
        return state

    async def _validate_blueprint(self, state: AgentState) -> AgentState:
        """Validate blueprint has all required components."""
        blueprint = state["output_data"].get("channel_blueprint", {})
        required_fields = [
            "channel_promise", "content_pillars", "voice_persona",
            "visual_identity", "series_library", "monetization_strategy"
        ]
        missing = [f for f in required_fields if f not in blueprint]
        state["output_data"]["blueprint_complete"] = len(missing) == 0
        state["output_data"]["missing_fields"] = missing
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


channel_architect_agent = ChannelArchitectAgent()
