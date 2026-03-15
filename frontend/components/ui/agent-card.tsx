"use client";

import { cn } from "@/lib/utils";
import { LAYER_COLORS } from "@/lib/constants";
import type { Agent } from "@/types";
import { Play, CheckCircle, XCircle, Clock, Pause } from "lucide-react";

const STATUS_ICONS = {
  idle: Clock,
  running: Play,
  completed: CheckCircle,
  error: XCircle,
  paused: Pause,
};

const STATUS_COLORS = {
  idle: "text-muted-foreground",
  running: "text-blue-500",
  completed: "text-green-500",
  error: "text-red-500",
  paused: "text-yellow-500",
};

interface AgentCardProps {
  agent: Agent;
  onRun?: (agentId: string) => void;
  compact?: boolean;
  className?: string;
}

export function AgentCard({ agent, onRun, compact = false, className }: AgentCardProps) {
  const layerColors = LAYER_COLORS[agent.layer] ?? LAYER_COLORS[1];
  const StatusIcon = STATUS_ICONS[agent.status as keyof typeof STATUS_ICONS] ?? Clock;
  const statusColor = STATUS_COLORS[agent.status as keyof typeof STATUS_COLORS] ?? "text-muted-foreground";

  return (
    <div
      className={cn(
        "bg-card border border-border rounded-lg p-3 hover:border-primary/30 transition-colors",
        className
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span
              className={cn(
                "text-xs font-medium px-1.5 py-0.5 rounded-full border",
                layerColors.bg,
                layerColors.text,
                layerColors.border
              )}
            >
              L{agent.layer}
            </span>
            <span className="text-sm font-semibold text-foreground truncate">{agent.name}</span>
          </div>
          {!compact && (
            <p className="text-xs text-muted-foreground leading-relaxed">{agent.description}</p>
          )}
        </div>
        <div className={cn("flex items-center gap-1 shrink-0", statusColor)}>
          <StatusIcon className={cn("w-4 h-4", agent.status === "running" && "animate-spin")} />
        </div>
      </div>

      {!compact && (
        <div className="mt-2 flex items-center justify-between">
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{agent.tasksCompleted} uruchomień</span>
            {agent.successRate > 0 && <span>{agent.successRate}% skuteczność</span>}
            <span>~{agent.avgDurationSeconds}s</span>
          </div>
          {onRun && agent.status === "idle" && (
            <button
              onClick={() => onRun(agent.id)}
              className="text-xs text-primary hover:underline font-medium"
            >
              Uruchom
            </button>
          )}
        </div>
      )}
    </div>
  );
}
