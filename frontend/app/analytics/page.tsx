"use client";

import { useState } from "react";
import { cn, formatNumber, formatPercent } from "@/lib/utils";
import { TrendingDown, AlertTriangle, CheckCircle, Eye, Clock } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, ReferenceLine,
} from "recharts";

const mockRetentionData = [
  { time: 0, retention: 100, label: "" },
  { time: 10, retention: 82, label: "" },
  { time: 20, retention: 74, label: "Hook end" },
  { time: 30, retention: 68, label: "" },
  { time: 60, retention: 61, label: "" },
  { time: 90, retention: 58, label: "Micro-payoff" },
  { time: 120, retention: 54, label: "" },
  { time: 180, retention: 52, label: "" },
  { time: 240, retention: 49, label: "DROP: transition slow" },
  { time: 300, retention: 47, label: "" },
  { time: 360, retention: 46, label: "Micro-payoff" },
  { time: 420, retention: 43, label: "" },
  { time: 480, retention: 41, label: "" },
  { time: 540, retention: 39, label: "DROP: off-topic" },
  { time: 600, retention: 38, label: "" },
  { time: 660, retention: 36, label: "" },
  { time: 720, retention: 35, label: "" },
  { time: 780, retention: 34, label: "" },
  { time: 840, retention: 32, label: "" },
  { time: 900, retention: 31, label: "Value peak" },
  { time: 960, retention: 33, label: "" },
  { time: 1020, retention: 30, label: "" },
  { time: 1080, retention: 28, label: "CTA start" },
];

const mockDropPoints = [
  { timestamp: "4:00", reason: "Transition slow — brak micro-payoff", severity: "yellow", loss: -3 },
  { timestamp: "9:00", reason: "Off-topic drift — za dlugi przyklad", severity: "yellow", loss: -2 },
  { timestamp: "0:20", reason: "Hook end — normalne odpadanie", severity: "green", loss: -8 },
];

const mockViewsTimeline = [
  { period: "2h", views: 340, ctr: 7.2, note: "Deploy watch" },
  { period: "24h", views: 2100, ctr: 6.8, note: "Stabilizacja" },
  { period: "72h", views: 5800, ctr: 6.5, note: "Suggested kick-in" },
  { period: "7d", views: 18200, ctr: 6.1, note: "Peak distribution" },
  { period: "28d", views: 42000, ctr: 5.8, note: "Long tail" },
];

const mockVideos = [
  { title: "5 Sekretow Inwestowania w ETF", views: 42000, avgRetention: 38, ctr: 6.1, revenue: 420 },
  { title: "ChatGPT vs Claude 2026", views: 28000, avgRetention: 44, ctr: 8.3, revenue: 280 },
  { title: "Top 10 Narzedzi AI 2026", views: 31000, avgRetention: 41, ctr: 7.1, revenue: 310 },
];

export default function AnalyticsPage() {
  const [selectedVideo, setSelectedVideo] = useState(0);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analytics & Forensics</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Agenci: Watch-Time Forensics • Experimentation • SEO Intelligence
          </p>
        </div>
      </div>

      {/* Video Selector */}
      <div className="flex gap-2">
        {mockVideos.map((v, i) => (
          <button
            key={i}
            onClick={() => setSelectedVideo(i)}
            className={cn(
              "text-xs px-3 py-2 rounded-lg border transition-colors text-left",
              selectedVideo === i
                ? "bg-primary/5 border-primary text-primary"
                : "border-border text-muted-foreground hover:border-primary/30"
            )}
          >
            <p className="font-medium truncate max-w-[160px]">{v.title}</p>
            <p>{formatNumber(v.views)} wysw. • {formatPercent(v.avgRetention)} retencji</p>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Wyswietlenia", value: formatNumber(mockVideos[selectedVideo].views), icon: Eye },
          { label: "Srednia Retencja", value: formatPercent(mockVideos[selectedVideo].avgRetention), icon: Clock },
          { label: "CTR", value: formatPercent(mockVideos[selectedVideo].ctr), icon: TrendingDown },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-card border border-border rounded-lg p-4 flex items-center gap-3">
            <Icon className="w-5 h-5 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-xl font-bold">{value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Retention Curve */}
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Krzywa Retencji</h2>
            <span className="text-xs text-muted-foreground">Watch-Time Forensics Agent</span>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={mockRetentionData}>
              <defs>
                <linearGradient id="retentionGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" tickFormatter={(v) => `${Math.floor(v / 60)}:${String(v % 60).padStart(2, "0")}`} tick={{ fontSize: 10 }} />
              <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 10 }} />
              <Tooltip
                formatter={(v: number) => [`${v}%`, "Retencja"]}
                labelFormatter={(l) => `${Math.floor(Number(l) / 60)}:${String(Number(l) % 60).padStart(2, "0")}`}
              />
              <ReferenceLine y={50} stroke="#fbbf24" strokeDasharray="4 4" label={{ value: "50%", fontSize: 10 }} />
              <Area type="monotone" dataKey="retention" stroke="#ef4444" fill="url(#retentionGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Drop Points Analysis */}
        <div className="bg-card border border-border rounded-lg p-4">
          <h2 className="font-semibold mb-3">Drop Points — Forensics</h2>
          <div className="space-y-2 mb-4">
            {mockDropPoints.map((dp, i) => (
              <div
                key={i}
                className={cn(
                  "flex items-start gap-2 p-2.5 rounded-lg border text-xs",
                  dp.severity === "yellow"
                    ? "bg-yellow-500/10 border-yellow-500/20"
                    : "bg-green-500/10 border-green-500/20"
                )}
              >
                {dp.severity === "yellow"
                  ? <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 shrink-0 mt-0.5" />
                  : <CheckCircle className="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" />
                }
                <div>
                  <span className="font-mono font-bold">{dp.timestamp}</span>
                  <span className="text-muted-foreground mx-1.5">—</span>
                  <span>{dp.reason}</span>
                  <span className={cn("ml-1.5 font-medium", dp.loss < -5 ? "text-red-500" : "text-yellow-500")}>
                    ({dp.loss}%)
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
            <p className="text-xs font-medium text-blue-700 mb-1">Rekomendacje agenta:</p>
            <ul className="text-xs text-blue-600 space-y-0.5">
              <li>• Skroc segment 3:30-4:30 o 40 sekund</li>
              <li>• Dodaj "pattern interrupt" wizualny przy 9:00</li>
              <li>• Intro mozna skrocic o 15s — hook dziala</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Post-publish Timeline */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h2 className="font-semibold mb-3">Post-Publish Timeline — Checkpoints</h2>
        <div className="flex items-start gap-0">
          {mockViewsTimeline.map((point, i) => (
            <div key={point.period} className="flex-1 relative">
              <div className="flex items-center mb-2">
                <div className="w-3 h-3 rounded-full bg-primary border-2 border-background z-10" />
                {i < mockViewsTimeline.length - 1 && (
                  <div className="flex-1 h-0.5 bg-primary/30" />
                )}
              </div>
              <div className="pr-2">
                <p className="text-xs font-bold">{point.period}</p>
                <p className="text-sm font-semibold">{formatNumber(point.views)}</p>
                <p className="text-xs text-muted-foreground">CTR: {formatPercent(point.ctr)}</p>
                <p className="text-xs text-blue-600 mt-0.5">{point.note}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
