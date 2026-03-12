import type { AgentId, PipelineStage } from "@/types";

// ============================================================
// Pipeline Stage Configuration
// ============================================================

export const PIPELINE_STAGES: { key: PipelineStage; label: string; icon: string }[] = [
  { key: "idea", label: "Idea", icon: "💡" },
  { key: "script", label: "Script", icon: "📝" },
  { key: "voice", label: "Voice", icon: "🎙️" },
  { key: "video", label: "Video", icon: "🎬" },
  { key: "thumbnail", label: "Thumbnail", icon: "🖼️" },
  { key: "seo", label: "SEO", icon: "🔍" },
  { key: "review", label: "Review", icon: "✅" },
  { key: "scheduled", label: "Scheduled", icon: "📅" },
  { key: "published", label: "Published", icon: "🚀" },
];

// ============================================================
// Agent Registry — 23 agents across 5 layers
// ============================================================

export interface AgentMeta {
  id: AgentId;
  name: string;
  layer: 1 | 2 | 3 | 4 | 5;
  description: string;
}

export const AGENT_REGISTRY: AgentMeta[] = [
  // Layer 1 — Market Intelligence
  { id: "niche_hunter", name: "Niche Hunter", layer: 1, description: "Discovers profitable YouTube niches using demand/competition analysis." },
  { id: "opportunity_mapper", name: "Opportunity Mapper", layer: 1, description: "Maps content gaps and trending opportunities within a niche." },
  { id: "competitive_deconstruction", name: "Competitive Deconstruction", layer: 1, description: "Analyzes top competitor channels to reverse-engineer their success." },

  // Layer 2 — Content Design
  { id: "channel_architect", name: "Channel Architect", layer: 2, description: "Designs channel strategy, content pillars, and brand identity." },
  { id: "script_strategist", name: "Script Strategist", layer: 2, description: "Generates retention-optimized scripts with hooks and story arcs." },
  { id: "voice_persona", name: "Voice Persona", layer: 2, description: "Defines and maintains consistent voice and tone across content." },

  // Layer 3 — AI Production
  { id: "hook_specialist", name: "Hook Specialist", layer: 3, description: "Creates and optimizes opening hooks for maximum retention." },
  { id: "retention_editor", name: "Retention Editor", layer: 3, description: "Injects retention devices and optimizes script pacing." },
  { id: "thumbnail_psychology", name: "Thumbnail Psychology", layer: 3, description: "Designs click-worthy thumbnails using psychological principles." },
  { id: "title_architect", name: "Title Architect", layer: 3, description: "Crafts high-CTR titles optimized for search and browse." },
  { id: "storyboard", name: "Storyboard", layer: 3, description: "Creates visual storyboards with scene-by-scene direction." },
  { id: "format_localizer", name: "Format Localizer", layer: 3, description: "Adapts content for different formats (Shorts, clips, podcasts)." },
  { id: "asset_retrieval", name: "Asset Retrieval", layer: 3, description: "Retrieves stock footage, images, and music for production." },
  { id: "video_assembly", name: "Video Assembly", layer: 3, description: "Assembles final video from voice, visuals, and effects." },
  { id: "audio_polish", name: "Audio Polish", layer: 3, description: "Enhances audio quality with noise removal and mastering." },
  { id: "caption", name: "Caption", layer: 3, description: "Generates accurate captions and subtitles." },

  // Layer 4 — Growth & Optimization
  { id: "seo_intelligence", name: "SEO Intelligence", layer: 4, description: "Optimizes titles, descriptions, and tags for YouTube search." },
  { id: "experimentation", name: "Experimentation", layer: 4, description: "Runs A/B tests on thumbnails, titles, and hooks." },
  { id: "watch_time_forensics", name: "Watch-Time Forensics", layer: 4, description: "Analyzes retention curves to identify and fix drop-off points." },
  { id: "channel_portfolio", name: "Channel Portfolio", layer: 4, description: "Manages multi-channel strategy and cross-promotion." },

  // Layer 5 — Compliance & Monetization
  { id: "originality_transformation", name: "Originality & Transformation", layer: 5, description: "Ensures content passes originality checks and adds transformative value." },
  { id: "rights_risk", name: "Rights & Risk", layer: 5, description: "Audits copyright, trademark, and fair use risks." },
  { id: "monetization_readiness", name: "Monetization Readiness", layer: 5, description: "Checks YPP eligibility and monetization compliance." },
];

// ============================================================
// Layer Configuration
// ============================================================

export const LAYER_NAMES: Record<number, string> = {
  1: "Market Intelligence",
  2: "Content Design",
  3: "AI Production",
  4: "Growth & Optimization",
  5: "Compliance & Monetization",
};

export const LAYER_COLORS: Record<number, { bg: string; text: string; border: string }> = {
  1: { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/20" },
  2: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/20" },
  3: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20" },
  4: { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/20" },
  5: { bg: "bg-red-500/10", text: "text-red-400", border: "border-red-500/20" },
};

// ============================================================
// Quality Gate Thresholds
// ============================================================

export const QUALITY_THRESHOLDS = {
  nicheScore: 70,
  hookScore: 8,
  originalityScore: 85,
  seoScore: 75,
  maxSimilarityCosine: 0.85,
  retentionTarget: 50,
  ctrTarget: 5.0,
} as const;
