"use client";

import { useState } from "react";
import { cn, PIPELINE_STAGE_LABELS, PIPELINE_STAGE_COLORS } from "@/lib/utils";
import { ScoreBadge } from "@/components/ui/score-badge";
import { Plus, GripVertical, Clock, Zap, Loader2, AlertCircle } from "lucide-react";
import type { PipelineStage, VideoProject } from "@/types";
import { useVideos } from "@/hooks/useApi";

const STAGES: PipelineStage[] = [
  "idea", "script", "voice", "video", "thumbnail", "seo", "review", "scheduled",
];

function VideoCard({ video }: { video: VideoProject }) {
  const agentCount = video.assignedAgents?.length ?? 0;
  const createdAt = new Date(video.createdAt);
  const daysAgo = Math.floor((Date.now() - createdAt.getTime()) / 86400000);

  return (
    <div className="bg-card border border-border rounded-lg p-2.5 hover:border-primary/30 transition-colors cursor-pointer group">
      <div className="flex items-start gap-1.5 mb-2">
        <GripVertical className="w-3 h-3 text-muted-foreground/40 mt-0.5 shrink-0 opacity-0 group-hover:opacity-100" />
        <p className="text-xs font-medium leading-snug">{video.title}</p>
      </div>

      {(video.hookScore ?? 0) > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">Hook {video.hookScore}</span>
          {(video.originalityScore ?? 0) > 0 && (
            <ScoreBadge score={video.originalityScore!} size="sm" label="Org" />
          )}
        </div>
      )}

      {agentCount > 0 && (
        <div className="flex items-center gap-1 mt-1.5">
          <Zap className="w-3 h-3 text-yellow-500" />
          <span className="text-xs text-muted-foreground">{agentCount} agentów aktywnych</span>
        </div>
      )}

      {daysAgo > 0 && (
        <div className="flex items-center gap-1 mt-1">
          <Clock className="w-3 h-3 text-muted-foreground/60" />
          <span className="text-xs text-muted-foreground">{daysAgo}d temu</span>
        </div>
      )}
    </div>
  );
}

export default function ContentPipelinePage() {
  const [activeStage, setActiveStage] = useState<PipelineStage | null>(null);
  const { data: videos = [], isLoading, error } = useVideos();

  const displayVideos = activeStage
    ? videos.filter((v) => v.stage === activeStage)
    : videos;

  return (
    <div className="p-6 h-full flex flex-col gap-4">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold">Pipeline Produkcji</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Kanban produkcji —{" "}
            {isLoading ? "..." : `${videos.length} aktywnych projektów`}
          </p>
        </div>
        <button className="bg-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-primary/90 flex items-center gap-1.5">
          <Plus className="w-4 h-4" />
          Nowy film
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-700 text-sm shrink-0">
          <AlertCircle className="w-4 h-4 shrink-0" />
          Błąd ładowania projektów. Sprawdź połączenie z API.
        </div>
      )}

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
          Wszystkie ({videos.length})
        </button>
        {STAGES.map((stage) => {
          const count = videos.filter((v) => v.stage === stage).length;
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

      {isLoading ? (
        <div className="flex items-center justify-center flex-1 text-muted-foreground gap-2">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Ładowanie projektów...</span>
        </div>
      ) : (
        /* Kanban Board */
        <div className="flex gap-3 overflow-x-auto pb-2 flex-1 min-h-0">
          {STAGES.map((stage) => {
            const stageVideos = displayVideos.filter((v) => v.stage === stage);
            return (
              <div key={stage} className="flex-none w-56">
                <div className={cn(
                  "flex items-center justify-between px-2 py-1.5 rounded-lg mb-2 text-xs font-medium",
                  PIPELINE_STAGE_COLORS[stage]
                )}>
                  <span>{PIPELINE_STAGE_LABELS[stage]}</span>
                  <span className="w-5 h-5 rounded-full bg-white/40 flex items-center justify-center text-xs font-bold">
                    {stageVideos.length}
                  </span>
                </div>

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
      )}
    </div>
  );
}
