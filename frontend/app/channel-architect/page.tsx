"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { AgentRunProgress } from "@/components/ui/agent-run-progress";
import { useNicheAnalyses, useRunAgent } from "@/hooks/useApi";
import type { NicheScore } from "@/types";
import {
  Layers,
  Mic,
  Image,
  TrendingUp,
  List,
  DollarSign,
  Loader2,
  Zap,
  ChevronDown,
} from "lucide-react";

interface ChannelBlueprint {
  channel_name?: string;
  channel_promise?: string;
  positioning?: string;
  target_audience?: {
    primary?: string;
    secondary?: string;
    pain_points?: string[];
    aspirations?: string[];
  };
  content_pillars?: Array<{
    name: string;
    description: string;
    video_types: string[];
    frequency: string;
  }>;
  voice_persona?: {
    name?: string;
    tone?: string;
    energy?: string;
    warmth?: string;
    key_phrases?: string[];
    avoid?: string[];
  };
  visual_identity?: {
    thumbnail_style?: string;
    color_palette?: string[];
    thumbnail_text_policy?: string;
    face_vs_graphic?: string;
  };
  series_library?: Array<{
    name: string;
    format: string;
    episode_count: string;
    cadence: string;
  }>;
  brand_rules?: string[];
  monetization_strategy?: {
    primary?: string;
    secondary?: string[];
    rpm_target?: number;
  };
}

export default function ChannelArchitectPage() {
  const [selectedNicheId, setSelectedNicheId] = useState<string | null>(null);
  const [requirements, setRequirements] = useState("");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [blueprint, setBlueprint] = useState<ChannelBlueprint | null>(null);

  const { data: niches = [], isLoading: nichesLoading } = useNicheAnalyses();
  const runAgent = useRunAgent();

  const selectedNiche = niches.find((n: NicheScore) => n.id === selectedNicheId) ?? null;

  function handleGenerate() {
    if (!selectedNiche) return;
    runAgent.mutate(
      {
        agentId: "channel_architect",
        input: {
          niche_name: selectedNiche.name,
          niche_analysis: JSON.stringify({
            overallScore: selectedNiche.overallScore,
            demandScore: selectedNiche.demandScore,
            competitionScore: selectedNiche.competitionScore,
            contentGaps: selectedNiche.contentGaps,
            estimatedMonthlyRpm: selectedNiche.estimatedMonthlyRpm,
          }),
          competitive_analysis: "",
          language: "pl",
          requirements: requirements.trim(),
        },
      },
      {
        onSuccess: (data) => {
          const runId = (data as Record<string, unknown>)?.id as string | undefined;
          if (runId) setActiveRunId(runId);
        },
      }
    );
  }

  function handleComplete(output: Record<string, unknown>) {
    const bp = output?.channel_blueprint ?? output?.blueprint ?? output;
    if (bp && typeof bp === "object") {
      setBlueprint(bp as ChannelBlueprint);
    }
    setActiveRunId(null);
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Layers className="w-6 h-6 text-primary" />
            Channel Architect
          </h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Agent: Channel Architect • Projektuje pozycjonowanie, filary tresci i DNA kanalu
          </p>
        </div>
      </div>

      {/* Config panel */}
      <div className="bg-card border border-border rounded-lg p-4 space-y-4">
        <h2 className="font-semibold text-sm">Konfiguracja Blueprintu</h2>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Nisza *</label>
            <div className="relative">
              <select
                value={selectedNicheId ?? ""}
                onChange={(e) => setSelectedNicheId(e.target.value || null)}
                className="w-full appearance-none px-3 py-2 text-sm bg-muted border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary pr-8"
              >
                <option value="">
                  {nichesLoading ? "Ladowanie nisz..." : "Wybierz nisza..."}
                </option>
                {niches.map((n: NicheScore) => (
                  <option key={n.id} value={n.id}>
                    {n.name} — {n.overallScore}/100
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
            </div>
            {niches.length === 0 && !nichesLoading && (
              <p className="text-xs text-yellow-600 mt-1">
                Brak analiz nisz. Przejdz do Niche Explorer.
              </p>
            )}
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Dodatkowe wymagania</label>
            <input
              type="text"
              placeholder="np. kanał edukacyjny, brak twarzy..."
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-muted border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {selectedNiche && (
          <div className="flex gap-4 p-3 bg-muted/50 rounded-lg text-xs text-muted-foreground">
            <span>Score: <strong className="text-foreground">{selectedNiche.overallScore}/100</strong></span>
            <span>Popyt: <strong className="text-foreground">{selectedNiche.demandScore}/100</strong></span>
            <span>RPM: <strong className="text-foreground">${selectedNiche.estimatedMonthlyRpm ?? "—"}</strong></span>
            {selectedNiche.overallScore < 70 && (
              <span className="text-yellow-600 ml-auto">Quality Gate: score &lt; 70 — ryzyko</span>
            )}
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={!selectedNiche || runAgent.isPending || !!activeRunId}
          className="bg-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
        >
          {(runAgent.isPending || activeRunId) && <Loader2 className="w-4 h-4 animate-spin" />}
          <Zap className="w-4 h-4" />
          Generuj Channel Blueprint
        </button>
      </div>

      {/* Agent progress */}
      {activeRunId && (
        <AgentRunProgress
          runId={activeRunId}
          onComplete={handleComplete}
          onError={() => setActiveRunId(null)}
        />
      )}

      {/* Blueprint output */}
      {blueprint && (
        <div className="space-y-4">
          {/* Channel identity */}
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h2 className="text-xl font-bold">{blueprint.channel_name ?? "—"}</h2>
                <p className="text-sm text-muted-foreground mt-1">{blueprint.channel_promise}</p>
              </div>
            </div>
            {blueprint.positioning && (
              <p className="text-sm bg-primary/5 border border-primary/20 rounded-lg px-3 py-2">
                <span className="text-xs font-medium text-primary uppercase tracking-wide block mb-0.5">Pozycjonowanie</span>
                {blueprint.positioning}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Content Pillars */}
            {blueprint.content_pillars && blueprint.content_pillars.length > 0 && (
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="font-semibold text-sm flex items-center gap-2 mb-3">
                  <Layers className="w-4 h-4 text-primary" />
                  Filary Tresci
                </h3>
                <div className="space-y-3">
                  {blueprint.content_pillars.map((pillar, i) => (
                    <div key={i} className="border-l-2 border-primary/40 pl-3">
                      <p className="text-sm font-medium">{pillar.name}</p>
                      <p className="text-xs text-muted-foreground">{pillar.description}</p>
                      <p className="text-xs text-primary mt-0.5">{pillar.frequency}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Voice Persona */}
            {blueprint.voice_persona && (
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="font-semibold text-sm flex items-center gap-2 mb-3">
                  <Mic className="w-4 h-4 text-blue-500" />
                  Voice Persona
                </h3>
                <div className="space-y-2">
                  {blueprint.voice_persona.name && (
                    <p className="text-sm font-medium">{blueprint.voice_persona.name}</p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {blueprint.voice_persona.tone && (
                      <span className="text-xs bg-blue-500/10 text-blue-700 px-2 py-0.5 rounded-full">{blueprint.voice_persona.tone}</span>
                    )}
                    {blueprint.voice_persona.energy && (
                      <span className="text-xs bg-green-500/10 text-green-700 px-2 py-0.5 rounded-full">energy: {blueprint.voice_persona.energy}</span>
                    )}
                  </div>
                  {blueprint.voice_persona.key_phrases && blueprint.voice_persona.key_phrases.length > 0 && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Kluczowe frazy:</p>
                      <div className="flex flex-wrap gap-1">
                        {blueprint.voice_persona.key_phrases.map((p, i) => (
                          <span key={i} className="text-xs bg-muted px-2 py-0.5 rounded">&quot;{p}&quot;</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Visual Identity */}
            {blueprint.visual_identity && (
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="font-semibold text-sm flex items-center gap-2 mb-3">
                  <Image className="w-4 h-4 text-purple-500" />
                  Identyfikacja Wizualna
                </h3>
                <div className="space-y-2">
                  {blueprint.visual_identity.thumbnail_style && (
                    <p className="text-xs text-muted-foreground">{blueprint.visual_identity.thumbnail_style}</p>
                  )}
                  {blueprint.visual_identity.color_palette && (
                    <div className="flex gap-1.5">
                      {blueprint.visual_identity.color_palette.map((color, i) => (
                        <div
                          key={i}
                          className="w-6 h-6 rounded border border-border"
                          style={{ backgroundColor: color }}
                          title={color}
                        />
                      ))}
                    </div>
                  )}
                  {blueprint.visual_identity.thumbnail_text_policy && (
                    <p className="text-xs bg-purple-500/10 text-purple-700 px-2 py-1 rounded">
                      {blueprint.visual_identity.thumbnail_text_policy}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Monetization */}
            {blueprint.monetization_strategy && (
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="font-semibold text-sm flex items-center gap-2 mb-3">
                  <DollarSign className="w-4 h-4 text-green-500" />
                  Strategia Monetyzacji
                </h3>
                <div className="space-y-2">
                  {blueprint.monetization_strategy.primary && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">Glowna:</span>
                      <span className="text-xs font-medium bg-green-500/10 text-green-700 px-2 py-0.5 rounded-full">
                        {blueprint.monetization_strategy.primary}
                      </span>
                    </div>
                  )}
                  {blueprint.monetization_strategy.rpm_target != null && (
                    <p className="text-xs text-muted-foreground">
                      RPM target: <strong className="text-foreground">${blueprint.monetization_strategy.rpm_target}/1000</strong>
                    </p>
                  )}
                  {blueprint.monetization_strategy.secondary && blueprint.monetization_strategy.secondary.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {blueprint.monetization_strategy.secondary.map((s, i) => (
                        <span key={i} className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded">{s}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Series Library */}
          {blueprint.series_library && blueprint.series_library.length > 0 && (
            <div className="bg-card border border-border rounded-lg p-4">
              <h3 className="font-semibold text-sm flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-orange-500" />
                Biblioteka Serii
              </h3>
              <div className="grid grid-cols-2 gap-3">
                {blueprint.series_library.map((series, i) => (
                  <div key={i} className="border border-border rounded-lg p-3">
                    <p className="text-sm font-medium">{series.name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{series.format}</p>
                    <div className="flex gap-2 mt-1.5">
                      <span className="text-xs bg-muted px-1.5 py-0.5 rounded">{series.cadence}</span>
                      <span className="text-xs bg-muted px-1.5 py-0.5 rounded">{series.episode_count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Brand Rules */}
          {blueprint.brand_rules && blueprint.brand_rules.length > 0 && (
            <div className="bg-card border border-border rounded-lg p-4">
              <h3 className="font-semibold text-sm flex items-center gap-2 mb-3">
                <List className="w-4 h-4 text-red-500" />
                Brand Rules
              </h3>
              <ul className="space-y-1.5">
                {blueprint.brand_rules.map((rule, i) => (
                  <li key={i} className={cn("text-xs flex items-start gap-2", i % 2 === 0 ? "text-foreground" : "text-muted-foreground")}>
                    <span className="text-primary font-bold shrink-0">{i + 1}.</span>
                    {rule}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {!blueprint && !activeRunId && (
        <div className="flex items-center justify-center py-16 text-muted-foreground text-center">
          <div>
            <Layers className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p className="text-sm">Wybierz nisza i kliknij &quot;Generuj Channel Blueprint&quot;</p>
            <p className="text-xs mt-1 opacity-60">Agent zaprojektuje caly kanal na podstawie analizy niszy</p>
          </div>
        </div>
      )}
    </div>
  );
}
