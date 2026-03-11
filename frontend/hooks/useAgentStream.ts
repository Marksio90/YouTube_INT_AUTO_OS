import { useEffect, useState, useRef } from "react";

interface AgentRunEvent {
  run_id: string;
  status: "pending" | "running" | "completed" | "error" | "cancelled";
  agent_id: string;
  output_data: Record<string, unknown> | null;
  error_message: string | null;
  duration_seconds: number | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useAgentStream(runId: string | null) {
  const [event, setEvent] = useState<AgentRunEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) return;

    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    const url = `${API_BASE_URL}/api/v1/agents/runs/${runId}/stream${token ? `?token=${token}` : ""}`;

    const es = new EventSource(url);
    esRef.current = es;
    setIsConnected(true);

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as AgentRunEvent;
        setEvent(data);
        if (data.status === "completed" || data.status === "error") {
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
    };

    return () => {
      es.close();
      setIsConnected(false);
    };
  }, [runId]);

  return { event, isConnected };
}
