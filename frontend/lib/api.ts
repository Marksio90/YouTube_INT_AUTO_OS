import axios from "axios";
import type {
  Channel,
  VideoProject,
  Script,
  Agent,
  AgentRun,
  VideoAnalytics,
  ComplianceReport,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach auth token from sessionStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const raw = sessionStorage.getItem("auth-storage");
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        const token = parsed?.state?.token;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch {
        // ignore malformed storage
      }
    }
  }
  return config;
});

// Global response interceptor — redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      const path = window.location.pathname;
      if (path !== "/login" && path !== "/register") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

// ============================================================
// Auth API
// ============================================================

export const authApi = {
  register: async (data: { email: string; password: string; full_name?: string }) => {
    const res = await api.post("/api/v1/auth/register", data);
    return res.data;
  },
  login: async (data: { email: string; password: string }) => {
    const res = await api.post("/api/v1/auth/login", data);
    return res.data;
  },
  me: async () => {
    const res = await api.get("/api/v1/auth/me");
    return res.data;
  },
  refresh: async (refreshToken: string) => {
    const res = await api.post("/api/v1/auth/refresh", { refresh_token: refreshToken });
    return res.data;
  },
};

// ============================================================
// Channels API
// ============================================================

export const channelsApi = {
  list: async (): Promise<Channel[]> => {
    const res = await api.get("/api/v1/channels");
    return res.data;
  },
  get: async (id: string): Promise<Channel> => {
    const res = await api.get(`/api/v1/channels/${id}`);
    return res.data;
  },
  create: async (data: Partial<Channel>): Promise<Channel> => {
    const res = await api.post("/api/v1/channels", data);
    return res.data;
  },
  update: async (id: string, data: Partial<Channel>): Promise<Channel> => {
    const res = await api.patch(`/api/v1/channels/${id}`, data);
    return res.data;
  },
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/channels/${id}`);
  },
};

// ============================================================
// Videos API
// ============================================================

export const videosApi = {
  list: async (channelId?: string, stage?: string): Promise<VideoProject[]> => {
    const params: Record<string, string> = {};
    if (channelId) params.channel_id = channelId;
    if (stage) params.stage = stage;
    const res = await api.get("/api/v1/videos", { params });
    return res.data;
  },
  get: async (id: string): Promise<VideoProject> => {
    const res = await api.get(`/api/v1/videos/${id}`);
    return res.data;
  },
  create: async (data: {
    channel_id: string;
    title: string;
    format?: string;
    niche?: string;
    target_keywords?: string[];
  }): Promise<VideoProject> => {
    const res = await api.post("/api/v1/videos", data);
    return res.data;
  },
  update: async (id: string, data: Record<string, unknown>): Promise<VideoProject> => {
    const res = await api.patch(`/api/v1/videos/${id}`, data);
    return res.data;
  },
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/videos/${id}`);
  },
  getAnalytics: async (id: string): Promise<VideoAnalytics> => {
    const res = await api.get(`/api/v1/videos/${id}/analytics`);
    return res.data;
  },
  getCompliance: async (id: string): Promise<ComplianceReport> => {
    const res = await api.get(`/api/v1/videos/${id}/compliance`);
    return res.data;
  },
};

// ============================================================
// Scripts API
// ============================================================

export const scriptsApi = {
  get: async (id: string): Promise<Script> => {
    const res = await api.get(`/api/v1/scripts/${id}`);
    return res.data;
  },
  generate: async (data: {
    video_project_id: string;
    topic: string;
    target_keywords?: string[];
    target_duration_minutes?: number;
    tone?: string;
    hook_type?: string;
  }): Promise<Script> => {
    const res = await api.post("/api/v1/scripts/generate", data);
    return res.data;
  },
};

// ============================================================
// Agents API
// ============================================================

export const agentsApi = {
  list: async (): Promise<Agent[]> => {
    const res = await api.get("/api/v1/agents");
    return res.data;
  },
  run: async (agentId: string, input: Record<string, unknown>): Promise<AgentRun> => {
    const res = await api.post(`/api/v1/agents/${agentId}/run`, input);
    return res.data;
  },
  getStatus: async (runId: string): Promise<AgentRun> => {
    const res = await api.get(`/api/v1/agents/runs/${runId}`);
    return res.data;
  },
};

// ============================================================
// Dashboard API
// ============================================================

export const dashboardApi = {
  getOverview: async () => {
    const res = await api.get("/api/v1/dashboard/overview");
    return res.data;
  },
  getAlerts: async () => {
    const res = await api.get("/api/v1/dashboard/alerts");
    return res.data;
  },
};

export default api;
