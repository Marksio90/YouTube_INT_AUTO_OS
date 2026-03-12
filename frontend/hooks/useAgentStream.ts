import { useEffect, useState, useRef, useCallback } from "react";

interface AgentRunEvent {
  run_id: string;
  status: "pending" | "running" | "completed" | "error" | "cancelled";
  agent_id: string;
  output_data: Record<string, unknown> | null;
  error_message: string | null;
  duration_seconds: number | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MAX_RECONNECT_ATTEMPTS = 5;

function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem("auth-storage");
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.state?.token ?? null;
  } catch {
    return null;
  }
}

export function useAgentStream(runId: string | null) {
  const [event, setEvent] = useState<AgentRunEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const attemptRef = useRef(0);
  const terminalRef = useRef(false);

  const connect = useCallback(() => {
    if (!runId || terminalRef.current) return;

    const token = getAuthToken();
    const url = `${API_BASE_URL}/api/v1/agents/runs/${runId}/stream${token ? `?token=${token}` : ""}`;

    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      attemptRef.current = 0;
    };

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as AgentRunEvent;
        setEvent(data);
        if (data.status === "completed" || data.status === "error" || data.status === "cancelled") {
          terminalRef.current = true;
          es.close();
          setIsConnected(false);
        }
      } catch {
        // ignore malformed SSE
      }
    };

    es.onerror = () => {
      es.close();
      setIsConnected(false);

      // Reconnect with exponential backoff unless terminal state reached
      if (!terminalRef.current && attemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(1000 * 2 ** attemptRef.current, 16000);
        attemptRef.current += 1;
        setTimeout(connect, delay);
      }
    };
  }, [runId]);

  useEffect(() => {
    terminalRef.current = false;
    attemptRef.current = 0;
    connect();

    return () => {
      terminalRef.current = true;
      esRef.current?.close();
      setIsConnected(false);
    };
  }, [connect]);

  return { event, isConnected };
}
