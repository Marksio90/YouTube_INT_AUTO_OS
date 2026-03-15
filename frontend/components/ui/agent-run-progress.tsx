"use client";

import { useEffect, useRef } from "react";
import { useAgentStream } from "@/hooks/useAgentStream";
import { cn } from "@/lib/utils";
import { CheckCircle, XCircle, Loader2, Zap, Wifi, WifiOff } from "lucide-react";

interface AgentRunProgressProps {
  runId: string | null;
  /** Called when the run completes successfully */
  onComplete?: (output: Record<string, unknown>) => void;
  /** Called when the run fails */
  onError?: (message: string) => void;
  className?: string;
}

const STATUS_LABEL: Record<string, string> = {
  pending: "Oczekuje w kolejce...",
  running: "Agent pracuje...",
  completed: "Zakończono",
  error: "Błąd",
  cancelled: "Anulowano",
};

const STATUS_COLOR: Record<string, string> = {
  pending: "text-muted-foreground",
  running: "text-blue-600",
  completed: "text-green-600",
  error: "text-red-600",
  cancelled: "text-yellow-600",
};

const PROGRESS_WIDTH: Record<string, string> = {
  pending: "w-1/4",
  running: "w-2/3",
  completed: "w-full",
  error: "w-full",
  cancelled: "w-1/3",
};

export function AgentRunProgress({
  runId,
  onComplete,
  onError,
  className,
}: AgentRunProgressProps) {
  const { event, isConnected } = useAgentStream(runId);
  const firedRef = useRef<string | null>(null);

  // Fire callbacks exactly once per terminal event (must not be called during render)
  useEffect(() => {
    if (!event || firedRef.current === event.status) return;
    if (event.status === "completed" && onComplete && event.output_data) {
      firedRef.current = event.status;
      onComplete(event.output_data);
    } else if (event.status === "error" && onError) {
      firedRef.current = event.status;
      onError(event.error_message ?? "Nieznany błąd");
    }
  }, [event, onComplete, onError]);

  if (!runId) return null;

  const status = event?.status ?? "pending";
  const isTerminal = status === "completed" || status === "error" || status === "cancelled";
  const isRunning = status === "running" || status === "pending";

  return (
    <div className={cn("bg-card border border-border rounded-lg p-4 space-y-3", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isRunning && <Loader2 className="w-4 h-4 animate-spin text-blue-500" />}
          {status === "completed" && <CheckCircle className="w-4 h-4 text-green-500" />}
          {status === "error" && <XCircle className="w-4 h-4 text-red-500" />}
          {status === "cancelled" && <XCircle className="w-4 h-4 text-yellow-500" />}
          <span className={cn("text-sm font-medium", STATUS_COLOR[status])}>
            {STATUS_LABEL[status]}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {isConnected
            ? <Wifi className="w-3 h-3 text-green-500" />
            : <WifiOff className="w-3 h-3 text-muted-foreground" />
          }
          <span className="text-xs text-muted-foreground font-mono truncate max-w-[120px]">
            {runId.slice(0, 8)}...
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
        <div
          className={cn(
            "h-1.5 rounded-full transition-all duration-700",
            PROGRESS_WIDTH[status],
            status === "completed" ? "bg-green-500" :
            status === "error" ? "bg-red-500" :
            isRunning ? "bg-blue-500 animate-pulse" : "bg-muted-foreground"
          )}
        />
      </div>

      {/* Agent info */}
      {event && (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Zap className="w-3 h-3" />
          <span>Agent: <strong>{event.agent_id}</strong></span>
          {event.duration_seconds && (
            <span className="ml-auto">{event.duration_seconds.toFixed(1)}s</span>
          )}
        </div>
      )}

      {/* Error message */}
      {status === "error" && event?.error_message && (
        <p className="text-xs text-red-600 bg-red-500/10 rounded px-2 py-1.5">
          {event.error_message}
        </p>
      )}
    </div>
  );
}
