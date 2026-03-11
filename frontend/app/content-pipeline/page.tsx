"use client";

import { useState } from "react";
import { cn, PIPELINE_STAGE_LABELS, PIPELINE_STAGE_COLORS } from "@/lib/utils";
import { ScoreBadge } from "@/components/ui/score-badge";
import { Plus, GripVertical, Clock, Zap } from "lucide-react";
import type { PipelineStage } from "@/types";

const STAGES: PipelineStage[] = [
  "idea", "script", "voice", "video", "thumbnail", "seo", "review", "scheduled",
];

const mockVideos = [
  { id: "1", title: "5 Sekretow Inwestowania w ETF 2026", stage: "script" as PipelineStage, channel: "AI Finanse PL", hookScore: 8.7, originalityScore: 84, seoScore: 79, agents: ["script_strategist", "hook_specialist"], daysInStage: 2 },
  { id: "2", title: "ChatGPT vs Claude – Ktory AI Wygrywa w 2026?", stage: "thumbnail" as PipelineStage, channel: "Technologia Przyszlosci", hookScore: 9.2, originalityScore: 91, seoScore: 88, agents: ["thumbnail_psychology", "title_architect"], daysInStage: 1 },
  { id: "3", title: "Jak Naucze Sie Angielskiego z AI w 90 Dni", stage: "voice" as PipelineStage, channel: "Edukacja Online", hookScore: 8.1, originalityScore: 78, seoScore: 72, agents: ["voice_persona", "audio_polish"], daysInStage: 1 },
  { id: "4", title: "Top 10 Narzedzi AI dla Freelancerow", stage: "seo" as PipelineStage, channel: "Technologia Przyszlosci", hookScore: 8.9, originalityScore: 88, seoScore: 82, agents: ["seo_intelligence"], daysInStage: 0 },
  { id: "5", title: "Psychologia Bogatych: 7 Nawykow Miliarderow", stage: "idea" as PipelineStage, channel: "AI Finanse PL", hookScore: 0, originalityScore: 0, seoScore: 0, agents: [], daysInStage: 3 },
  { id: "6", title: "Home Assistant 2026: Kompletny Przewodnik", stage: "video" as PipelineStage, channel: "Technologia Przyszlosci", hookScore: 7.8, originalityScore: 82, seoScore: 75, agents: ["video_assembly", "storyboard"], daysInStage: 2 },
  { id: "7", title: "Dieta Ketogeniczna – Co Nauka Mowi w 2026?", stage: "review" as PipelineStage, channel: "Edukacja Online", hookScore: 8.4, originalityScore: 86, seoScore: 81, agents: ["originality_transformation", "rights_risk"], daysInStage: 1 },
  { id: "8", title: "Make.com vs n8n – Ktora Automatyzacja Lepsza?", stage: "scheduled" as PipelineStage, channel: "Technologia Przyszlosci", hookScore: 9.0, originalityScore: 90, seoScore: 85, agents: [], daysInStage: 0 },
];

interface VideoCardProps {
  video: (typeof mockVideos)[0];
}

function VideoCard({ video }: VideoCardProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-2.5 hover:border-primary/30 transition-colors cursor-pointer group">
      <div className="flex items-start gap-1.5 mb-2">
        <GripVertical className="w-3 h-3 text-muted-foreground/40 mt-0.5 shrink-0 opacity-0 group-hover:opacity-100" />
        <p className="text-xs font-medium leading-snug">{video.title}</p>
      </div>
      <p className="text-xs text-muted-foreground mb-2">{video.channel}</p>

      {video.hookScore > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">Hook {video.hookScore}</span>
          <ScoreBadge score={video.originalityScore} size="sm" label="Org" />
        </div>
      )}

      {video.agents.length > 0 && (
        <div className="flex items-center gap-1 mt-1.5">
          <Zap className="w-3 h-3 text-yellow-500" />
          <span className="text-xs text-muted-foreground">{video.agents.length} agentow aktywnych</span>
        </div>
      )}

      {video.daysInStage > 0 && (
        <div className="flex items-center gap-1 mt-1">
          <Clock className="w-3 h-3 text-muted-foreground/60" />
          <span className="text-xs text-muted-foreground">{video.daysInStage}d w tym etapie</span>
        </div>
      )}
    </div>
  );
}

export default function ContentPipelinePage() {
  const [activeStage, setActiveStage] = useState<PipelineStage | null>(null);

  return (
    <div className="p-6 h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold">Content Pipeline</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Kanban produkcji — {mockVideos.length} aktywnych projektow
          </p>
        </div>
        <button className="bg-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-primary/90 flex items-center gap-1.5">
          <Plus className="w-4 h-4" />
          Nowy film
        </button>
      </div>

      {/* Stage filters */}
      <div className="flex gap-2 overflow-x-auto pb-1 shrink-0">
        <button
          onClick={() => setActiveStage(null)}
          className={cn(
            "text-xs px-3 py-1.5 rounded-full border whitespace-nowrap transition-colors",
            activeStage === null
              ? "bg-primary text-white border-primary"
              : "border-border text-muted-foreground hover:border-primary/50"
          )}
        >
          Wszystkie ({mockVideos.length})
        </button>
        {STAGES.map((stage) => {
          const count = mockVideos.filter((v) => v.stage === stage).length;
          return (
            <button
              key={stage}
              onClick={() => setActiveStage(stage === activeStage ? null : stage)}
              className={cn(
                "text-xs px-3 py-1.5 rounded-full border whitespace-nowrap transition-colors",
                activeStage === stage
                  ? "bg-primary text-white border-primary"
                  : "border-border text-muted-foreground hover:border-primary/50"
              )}
            >
              {PIPELINE_STAGE_LABELS[stage]} {count > 0 && `(${count})`}
            </button>
          );
        })}
      </div>

      {/* Kanban Board */}
      <div className="flex gap-3 overflow-x-auto pb-2 flex-1 min-h-0">
        {STAGES.map((stage) => {
          const stageVideos = mockVideos.filter(
            (v) => v.stage === stage && (!activeStage || v.stage === activeStage)
          );
          return (
            <div key={stage} className="flex-none w-56">
              {/* Column Header */}
              <div className={cn(
                "flex items-center justify-between px-2 py-1.5 rounded-lg mb-2 text-xs font-medium",
                PIPELINE_STAGE_COLORS[stage]
              )}>
                <span>{PIPELINE_STAGE_LABELS[stage]}</span>
                <span className="w-5 h-5 rounded-full bg-white/40 flex items-center justify-center text-xs font-bold">
                  {stageVideos.length}
                </span>
              </div>

              {/* Cards */}
              <div className="space-y-2">
                {stageVideos.map((video) => (
                  <VideoCard key={video.id} video={video} />
                ))}
                <button className="w-full text-xs text-muted-foreground hover:text-foreground py-2 border border-dashed border-border/60 rounded-lg hover:border-primary/40 transition-colors flex items-center justify-center gap-1">
                  <Plus className="w-3 h-3" />
                  Dodaj
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
