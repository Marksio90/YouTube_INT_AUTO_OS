import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  channelsApi,
  videosApi,
  agentsApi,
  dashboardApi,
  scriptsApi,
  nichesApi,
  authApi,
} from "@/lib/api";

// ============================================================
// Auth Hooks
// ============================================================

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: authApi.me,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

// ============================================================
// Dashboard Hooks
// ============================================================

export function useDashboardOverview() {
  return useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: dashboardApi.getOverview,
    refetchInterval: 30_000, // Refresh every 30s
    retry: 1,
  });
}

export function useDashboardAlerts() {
  return useQuery({
    queryKey: ["dashboard", "alerts"],
    queryFn: dashboardApi.getAlerts,
    refetchInterval: 60_000,
    retry: 1,
  });
}

// ============================================================
// Channel Hooks
// ============================================================

export function useChannels() {
  return useQuery({
    queryKey: ["channels"],
    queryFn: channelsApi.list,
    retry: 1,
  });
}

export function useChannel(id: string) {
  return useQuery({
    queryKey: ["channels", id],
    queryFn: () => channelsApi.get(id),
    enabled: !!id,
  });
}

export function useCreateChannel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: channelsApi.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["channels"] }),
  });
}

// ============================================================
// Video Hooks
// ============================================================

export function useVideos(channelId?: string, stage?: string) {
  return useQuery({
    queryKey: ["videos", { channelId, stage }],
    queryFn: () => videosApi.list(channelId, stage),
    retry: 1,
  });
}

export function useVideo(id: string) {
  return useQuery({
    queryKey: ["videos", id],
    queryFn: () => videosApi.get(id),
    enabled: !!id,
  });
}

export function useVideoAnalytics(id: string) {
  return useQuery({
    queryKey: ["videos", id, "analytics"],
    queryFn: () => videosApi.getAnalytics(id),
    enabled: !!id,
    refetchInterval: 5 * 60 * 1000,
  });
}

// ============================================================
// Agent Hooks
// ============================================================

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list,
    refetchInterval: 10_000, // Refresh every 10s to show live status
    retry: 1,
  });
}

export function useAgentRun(runId: string) {
  return useQuery({
    queryKey: ["agent-runs", runId],
    queryFn: () => agentsApi.getStatus(runId),
    enabled: !!runId,
    refetchInterval: (query) => {
      // Poll every 2s while running
      const data = query.state.data as { status?: string } | undefined;
      if (data?.status === "running" || data?.status === "pending") return 2000;
      return false;
    },
  });
}

export function useRunAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ agentId, input }: { agentId: string; input: Record<string, unknown> }) =>
      agentsApi.run(agentId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["agents"] }),
  });
}

// ============================================================
// Script Hooks
// ============================================================

export function useScript(id: string) {
  return useQuery({
    queryKey: ["scripts", id],
    queryFn: () => scriptsApi.get(id),
    enabled: !!id,
  });
}

export function useGenerateScript() {
  return useMutation({
    mutationFn: scriptsApi.generate,
  });
}

// ============================================================
// Niche Hooks
// ============================================================


export function useNicheAnalyses(channelId?: string) {
  return useQuery({
    queryKey: ["niches", { channelId }],
    queryFn: () => nichesApi.list(channelId),
    retry: 1,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRunNicheAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: nichesApi.analyze,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["niches"] }),
  });
}
