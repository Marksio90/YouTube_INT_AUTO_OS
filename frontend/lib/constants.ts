import type { AgentId, PipelineStage } from "@/types";

// ============================================================
// Pipeline Stage Configuration
// ============================================================

export const PIPELINE_STAGES: { key: PipelineStage; label: string; icon: string }[] = [
  { key: "idea", label: "Pomysł", icon: "💡" },
  { key: "script", label: "Skrypt", icon: "📝" },
  { key: "voice", label: "Nagranie", icon: "🎙️" },
  { key: "video", label: "Wideo", icon: "🎬" },
  { key: "thumbnail", label: "Miniatura", icon: "🖼️" },
  { key: "seo", label: "SEO", icon: "🔍" },
  { key: "review", label: "Recenzja", icon: "✅" },
  { key: "scheduled", label: "Zaplanowany", icon: "📅" },
  { key: "published", label: "Opublikowany", icon: "🚀" },
];

// ============================================================
// Agent Registry — 23 agentów w 5 warstwach
// ============================================================

export interface AgentMeta {
  id: AgentId;
  name: string;
  layer: 1 | 2 | 3 | 4 | 5;
  description: string;
}

export const AGENT_REGISTRY: AgentMeta[] = [
  // Warstwa 1 — Wywiad Rynkowy
  { id: "niche_hunter", name: "Łowca Nisz", layer: 1, description: "Odkrywa dochodowe nisze YouTube na podstawie analizy popytu i konkurencji." },
  { id: "opportunity_mapper", name: "Maper Okazji", layer: 1, description: "Mapuje luki contentowe i trendy w obrębie niszy." },
  { id: "competitive_deconstruction", name: "Dekonstrukcja Konkurencji", layer: 1, description: "Analizuje czołowe kanały konkurencji, aby odwrócić inżynierię ich sukcesu." },

  // Warstwa 2 — Projektowanie Treści
  { id: "channel_architect", name: "Architekt Kanału", layer: 2, description: "Projektuje strategię kanału, filary treści i tożsamość marki." },
  { id: "script_strategist", name: "Strateg Skryptów", layer: 2, description: "Generuje skrypty zoptymalizowane pod retencję z hookami i łukami fabularnymi." },
  { id: "voice_persona", name: "Persona Głosowa", layer: 2, description: "Definiuje i utrzymuje spójny głos i ton we wszystkich treściach." },

  // Warstwa 3 — Produkcja AI
  { id: "hook_specialist", name: "Specjalista od Hooków", layer: 3, description: "Tworzy i optymalizuje otwierające hooki dla maksymalnej retencji." },
  { id: "retention_editor", name: "Edytor Retencji", layer: 3, description: "Wstrzykuje elementy retencji i optymalizuje tempo skryptu." },
  { id: "thumbnail_psychology", name: "Psychologia Miniatur", layer: 3, description: "Projektuje przyciągające kliknięcia miniatury z użyciem zasad psychologicznych." },
  { id: "title_architect", name: "Architekt Tytułów", layer: 3, description: "Tworzy tytuły o wysokim CTR, zoptymalizowane pod wyszukiwanie i przeglądanie." },
  { id: "storyboard", name: "Storyboard", layer: 3, description: "Tworzy wizualne storyboardy z kadr-po-kadrze wskazówkami." },
  { id: "format_localizer", name: "Lokalizator Formatów", layer: 3, description: "Dostosowuje treści do różnych formatów (Shorts, klipy, podcasty)." },
  { id: "asset_retrieval", name: "Pobieranie Zasobów", layer: 3, description: "Pobiera materiały stockowe, obrazy i muzykę do produkcji." },
  { id: "video_assembly", name: "Montaż Wideo", layer: 3, description: "Montuje finalne wideo z głosu, wizualizacji i efektów." },
  { id: "audio_polish", name: "Polerowanie Audio", layer: 3, description: "Poprawia jakość dźwięku przez usuwanie szumów i mastering." },
  { id: "caption", name: "Napisy", layer: 3, description: "Generuje dokładne napisy i podpisy." },

  // Warstwa 4 — Wzrost i Optymalizacja
  { id: "seo_intelligence", name: "Inteligencja SEO", layer: 4, description: "Optymalizuje tytuły, opisy i tagi pod wyszukiwarkę YouTube." },
  { id: "experimentation", name: "Eksperymentowanie", layer: 4, description: "Prowadzi testy A/B miniatur, tytułów i hooków." },
  { id: "watch_time_forensics", name: "Analiza Czasu Oglądania", layer: 4, description: "Analizuje krzywe retencji, aby identyfikować i naprawiać momenty odpadu." },
  { id: "channel_portfolio", name: "Portfolio Kanałów", layer: 4, description: "Zarządza strategią wielu kanałów i wzajemną promocją." },

  // Warstwa 5 — Zgodność i Monetyzacja
  { id: "originality_transformation", name: "Oryginalność i Transformacja", layer: 5, description: "Zapewnia przejście treści przez kontrole oryginalności i dodaje wartość transformacyjną." },
  { id: "rights_risk", name: "Prawa i Ryzyko", layer: 5, description: "Audytuje ryzyko praw autorskich, znaków towarowych i dozwolonego użytku." },
  { id: "monetization_readiness", name: "Gotowość do Monetyzacji", layer: 5, description: "Sprawdza kwalifikowalność do YPP i zgodność z zasadami monetyzacji." },
];

// ============================================================
// Layer Configuration
// ============================================================

export const LAYER_NAMES: Record<number, string> = {
  1: "Wywiad Rynkowy",
  2: "Projektowanie Treści",
  3: "Produkcja AI",
  4: "Wzrost i Optymalizacja",
  5: "Zgodność i Monetyzacja",
};

export const LAYER_COLORS: Record<number, { bg: string; text: string; border: string }> = {
  1: { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/20" },
  2: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/20" },
  3: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20" },
  4: { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/20" },
  5: { bg: "bg-red-500/10", text: "text-red-400", border: "border-red-500/20" },
};

/** Alias dla AGENT_REGISTRY — używany przez dashboard i inne komponenty */
export const AGENTS = AGENT_REGISTRY;

// ============================================================
// Progi Quality Gate
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
