"use client";

import { useDashboardOverview, useDashboardAlerts, useChannels, useAgents } from "@/hooks/useApi";
import { StatCard } from "@/components/ui/stat-card";
import { ScoreBadge } from "@/components/ui/score-badge";
import { AgentCard } from "@/components/ui/agent-card";
import { AGENTS, LAYER_COLORS } from "@/lib/constants";
import { formatNumber, formatCurrency, PIPELINE_STAGE_LABELS, PIPELINE_STAGE_COLORS, cn } from "@/lib/utils";
import {
  Users,
  Eye,
  Clock,
  DollarSign,
  AlertTriangle,
  TrendingUp,
  CheckCircle,
  Youtube,
  Zap,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";

// Mock data for dashboard
const mockViewsData = [
  { date: "Jan", views: 12000, watchHours: 850, revenue: 180 },
  { date: "Feb", views: 18000, watchHours: 1200, revenue: 240 },
  { date: "Mar", views: 15000, watchHours: 1050, revenue: 210 },
  { date: "Apr", views: 24000, watchHours: 1680, revenue: 320 },
  { date: "May", views: 32000, watchHours: 2240, revenue: 450 },
  { date: "Jun", views: 28000, watchHours: 1960, revenue: 380 },
  { date: "Jul", views: 41000, watchHours: 2870, revenue: 560 },
  { date: "Aug", views: 52000, watchHours: 3640, revenue: 720 },
  { date: "Sep", views: 47000, watchHours: 3290, revenue: 650 },
  { date: "Oct", views: 63000, watchHours: 4410, revenue: 890 },
  { date: "Nov", views: 71000, watchHours: 4970, revenue: 1050 },
  { date: "Dec", views: 85000, watchHours: 5950, revenue: 1280 },
];

const mockChannels = [
  {
    name: "AI Finanse PL",
    niche: "Finanse",
    subscribers: 4821,
    views: 312000,
    revenue: 3240,
    complianceScore: 92,
    originalityScore: 87,
    yppStatus: "active",
    videoCount: 48,
  },
  {
    name: "Technologia Przyszlosci",
    niche: "AI & Tech",
    subscribers: 2340,
    views: 145000,
    revenue: 1180,
    complianceScore: 88,
    originalityScore: 82,
    yppStatus: "active",
    videoCount: 31,
  },
  {
    name: "Edukacja Online",
    niche: "Edukacja",
    subscribers: 890,
    views: 43000,
    revenue: 320,
    complianceScore: 95,
    originalityScore: 91,
    yppStatus: "pending",
    videoCount: 14,
  },
];

const mockPipelineStats = [
  { stage: "idea", count: 12 },
  { stage: "script", count: 8 },
  { stage: "voice", count: 5 },
  { stage: "video", count: 4 },
  { stage: "thumbnail", count: 3 },
  { stage: "seo", count: 2 },
  { stage: "review", count: 3 },
  { stage: "scheduled", count: 6 },
  { stage: "published", count: 93 },
];

const mockAlerts = [
  {
    type: "warning",
    message: 'Video "5 Sekretow Inwestowania" ma similarity score 0.87 - ryzyko inauthentic content',
    time: "2h temu",
  },
  {
    type: "info",
    message: "Kanal AI Finanse PL: 4,821/5,000 subskrybentow - YPP upgrade w zasiegu",
    time: "4h temu",
  },
  {
    type: "success",
    message: 'Eksperyment A/B miniatur dla "ChatGPT vs Claude" zakonczony - wariant B wygrywa (+34% CTR)',
    time: "6h temu",
  },
  {
    type: "warning",
    message: "Kanal Edukacja Online: Watch hours 2,890/4,000 - kontynuuj produkcje",
    time: "1 dzien temu",
  },
];

const revenueByStreamData = [
  { name: "AdSense", value: 45 },
  { name: "Afiliacja", value: 30 },
  { name: "Sponsoring", value: 15 },
  { name: "Digital Products", value: 10 },
];
const PIE_COLORS = ["#ef4444", "#3b82f6", "#8b5cf6", "#f59e0b"];

export default function DashboardPage() {
  // Real API data — falls back to mock data if API is unavailable
  const { data: overview } = useDashboardOverview();
  const { data: apiAlerts } = useDashboardAlerts();
  const { data: apiChannels } = useChannels();
  const { data: apiAgents } = useAgents();

  // Merge real data with mock fallback
  const channels = (apiChannels as typeof mockChannels | null) ?? mockChannels;
  const alerts = (apiAlerts as typeof mockAlerts | null) ?? mockAlerts;
  const agentList = apiAgents ?? AGENTS;

  const totalRevenue = overview?.total_revenue ?? mockChannels.reduce((s, c) => s + c.revenue, 0);
  const totalSubscribers = overview?.total_subscribers ?? mockChannels.reduce((s, c) => s + c.subscribers, 0);
  const totalViews = overview?.total_views ?? mockChannels.reduce((s, c) => s + c.views, 0);
  const activeAgents = (agentList as Array<{status?: string}>).filter((a) => a.status === "running").length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Youtube className="w-7 h-7 text-primary" />
            Dashboard Główny
          </h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Portfolio: {channels.length} kanały | Marzec 2026
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Agenci:</span>
          <span className={cn("text-xs font-medium px-2 py-1 rounded-full",
            activeAgents > 0 ? "bg-green-500/10 text-green-600" : "bg-muted text-muted-foreground"
          )}>
            {activeAgents > 0 ? `${activeAgents} aktywnych` : "Brak aktywnych"}
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Łączne Przychody"
          value={formatCurrency(totalRevenue)}
          change={22}
          changeLabel="vs ostatni miesiac"
          icon={DollarSign}
          iconColor="text-green-600"
        />
        <StatCard
          title="Subskrybenci"
          value={formatNumber(totalSubscribers)}
          change={18}
          changeLabel="vs ostatni miesiac"
          icon={Users}
          iconColor="text-blue-600"
        />
        <StatCard
          title="Wyświetlenia"
          value={formatNumber(totalViews)}
          change={31}
          changeLabel="vs ostatni miesiac"
          icon={Eye}
          iconColor="text-purple-600"
        />
        <StatCard
          title="Filmy w Pipeline"
          value={mockPipelineStats.reduce((s, p) => s + p.count, 0) - 93}
          subtitle="Aktywne produkcje"
          icon={Clock}
          iconColor="text-orange-600"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Views Chart - 2 cols */}
        <div className="col-span-2 bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-foreground">Wyświetlenia & Przychody (12 msc)</h2>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-primary inline-block"/> Wyświetlenia</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 inline-block"/> Przychody ($)</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={mockViewsData}>
              <defs>
                <linearGradient id="viewsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="views"
                stroke="#ef4444"
                fill="url(#viewsGrad)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#22c55e"
                fill="url(#revenueGrad)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Revenue by Stream */}
        <div className="bg-card border border-border rounded-lg p-4">
          <h2 className="font-semibold text-foreground mb-4">Przychody wg Źródła</h2>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie
                data={revenueByStreamData}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={70}
                paddingAngle={3}
                dataKey="value"
              >
                {revenueByStreamData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => `${v}%`} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-2">
            {revenueByStreamData.map((item, i) => (
              <div key={item.name} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: PIE_COLORS[i] }}
                  />
                  <span className="text-muted-foreground">{item.name}</span>
                </span>
                <span className="font-medium">{item.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Channels Table */}
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-foreground">Portfolio Kanałów</h2>
          <button className="text-xs text-primary hover:underline">+ Dodaj kanał</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-3 text-xs text-muted-foreground font-medium">Kanal</th>
                <th className="text-right py-2 px-3 text-xs text-muted-foreground font-medium">Subskrybenci</th>
                <th className="text-right py-2 px-3 text-xs text-muted-foreground font-medium">Wyświetlenia</th>
                <th className="text-right py-2 px-3 text-xs text-muted-foreground font-medium">Przychody</th>
                <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">Compliance</th>
                <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">Oryginalność</th>
                <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">YPP</th>
              </tr>
            </thead>
            <tbody>
              {channels.map((channel) => (
                <tr key={channel.name} className="border-b border-border/50 hover:bg-muted/30">
                  <td className="py-3 px-3">
                    <div>
                      <p className="font-medium text-foreground">{channel.name}</p>
                      <p className="text-xs text-muted-foreground">{channel.niche} • {channel.videoCount} filmów</p>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-sm">
                    {formatNumber(channel.subscribers)}
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-sm">
                    {formatNumber(channel.views)}
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-sm text-green-600 font-medium">
                    {formatCurrency(channel.revenue)}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <ScoreBadge score={channel.complianceScore} size="sm" />
                  </td>
                  <td className="py-3 px-3 text-center">
                    <ScoreBadge score={channel.originalityScore} size="sm" />
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className={cn(
                      "text-xs px-2 py-0.5 rounded-full font-medium",
                      channel.yppStatus === "active"
                        ? "bg-green-500/10 text-green-600"
                        : "bg-yellow-500/10 text-yellow-600"
                    )}>
                      {channel.yppStatus === "active" ? "Aktywny" : "Oczekuje"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pipeline + Alerts Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Pipeline Distribution */}
        <div className="bg-card border border-border rounded-lg p-4">
          <h2 className="font-semibold text-foreground mb-3">Pipeline Produkcji</h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={mockPipelineStats.filter((s) => s.stage !== "published")}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="stage"
                tick={{ fontSize: 10 }}
                tickFormatter={(s) => PIPELINE_STAGE_LABELS[s] || s}
              />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip
                labelFormatter={(label) => PIPELINE_STAGE_LABELS[label] || label}
              />
              <Bar dataKey="count" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Alerts */}
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-foreground">Alerty i Powiadomienia</h2>
            <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
              {alerts.length} nowe
            </span>
          </div>
          <div className="space-y-2">
            {alerts.map((alert, i) => (
              <div
                key={i}
                className={cn(
                  "flex gap-2 p-2 rounded-lg text-xs",
                  alert.type === "warning" && "bg-yellow-500/10 border border-yellow-500/20",
                  alert.type === "success" && "bg-green-500/10 border border-green-500/20",
                  alert.type === "info" && "bg-blue-500/10 border border-blue-500/20"
                )}
              >
                {alert.type === "warning" && <AlertTriangle className="w-3 h-3 text-yellow-500 shrink-0 mt-0.5" />}
                {alert.type === "success" && <CheckCircle className="w-3 h-3 text-green-500 shrink-0 mt-0.5" />}
                {alert.type === "info" && <TrendingUp className="w-3 h-3 text-blue-500 shrink-0 mt-0.5" />}
                <div>
                  <p className="text-foreground leading-relaxed">{alert.message}</p>
                  <p className="text-muted-foreground mt-0.5">{alert.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Agent Overview */}
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-foreground flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            23 Agentów AI — Status
          </h2>
          <div className="flex gap-3 text-xs">
            {[1, 2, 3, 4, 5].map((layer) => (
              <span
                key={layer}
                className={cn(
                  "px-2 py-0.5 rounded-full border text-xs",
                  LAYER_COLORS[layer].bg,
                  LAYER_COLORS[layer].text,
                  LAYER_COLORS[layer].border
                )}
              >
                L{layer}: {(agentList as Array<{layer?: number}>).filter((a) => a.layer === layer).length}
              </span>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
          {(agentList as typeof AGENTS).map((agent) => (
            <AgentCard key={agent.id} agent={agent} compact />
          ))}
        </div>
      </div>
    </div>
  );
}
