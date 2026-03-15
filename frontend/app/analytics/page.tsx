"use client";

import { useState } from "react";
import { cn, formatNumber, formatPercent } from "@/lib/utils";
import { TrendingDown, AlertTriangle, CheckCircle, Eye, Clock, Loader2, AlertCircle } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { useVideos, useVideoAnalytics } from "@/hooks/useApi";
import type { VideoProject, RetentionDataPoint } from "@/types";

export default function AnalyticsPage() {
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);

  const { data: videos = [], isLoading: videosLoading } = useVideos();
  const publishedVideos = videos.filter((v: VideoProject) =>
    v.stage === "published" || v.stage === "scheduled"
  );

  const activeVideo = selectedVideoId
    ? publishedVideos.find((v: VideoProject) => v.id === selectedVideoId) ?? publishedVideos[0]
    : publishedVideos[0];

  const { data: analytics, isLoading: analyticsLoading } = useVideoAnalytics(activeVideo?.id ?? "");

  const isLoading = videosLoading || analyticsLoading;

  const retentionData = (analytics?.retentionCurve ?? []).map((pt: RetentionDataPoint) => ({
    time: pt.timestampSeconds,
    retention: pt.retentionPercent,
    isDropPoint: pt.isDropPoint,
    dropReason: pt.dropReason,
  }));

  const dropPoints = retentionData.filter((pt) => pt.isDropPoint);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analityka i Diagnostyka</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Agenci: Analiza Czasu Oglądania • Eksperymentowanie • Inteligencja SEO
          </p>
        </div>
      </div>

      {/* Video Selector */}
      {videosLoading ? (
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Ładowanie filmów...
        </div>
      ) : publishedVideos.length === 0 ? (
        <div className="flex items-center gap-2 p-4 bg-muted rounded-lg text-muted-foreground text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          Brak opublikowanych filmów. Dane analityczne będą dostępne po publikacji.
        </div>
      ) : (
        <div className="flex gap-2 flex-wrap">
          {publishedVideos.map((v: VideoProject) => (
            <button
              key={v.id}
              onClick={() => setSelectedVideoId(v.id)}
              className={cn(
                "text-xs px-3 py-2 rounded-lg border transition-colors text-left",
                (activeVideo?.id === v.id)
                  ? "bg-primary/5 border-primary text-primary"
                  : "border-border text-muted-foreground hover:border-primary/30"
              )}
            >
              <p className="font-medium truncate max-w-[160px]">{v.title}</p>
            </button>
          ))}
        </div>
      )}

      {analyticsLoading && activeVideo && (
        <div className="flex items-center justify-center py-12 text-muted-foreground gap-2">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Ładowanie analityki...</span>
        </div>
      )}

      {analytics && (
        <>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Wyświetlenia", value: formatNumber(analytics.views), icon: Eye },
              { label: "Średnia Retencja", value: formatPercent(analytics.avgRetentionPercent), icon: Clock },
              { label: "CTR", value: formatPercent(analytics.ctr), icon: TrendingDown },
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
                <span className="text-xs text-muted-foreground">Agent: Analiza Czasu Oglądania</span>
              </div>
              {retentionData.length > 0 ? (
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={retentionData}>
                    <defs>
                      <linearGradient id="retentionGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="time"
                      tickFormatter={(v) => `${Math.floor(v / 60)}:${String(v % 60).padStart(2, "0")}`}
                      tick={{ fontSize: 10 }}
                    />
                    <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 10 }} />
                    <Tooltip
                      formatter={(v: number) => [`${v}%`, "Retencja"]}
                      labelFormatter={(l) => `${Math.floor(Number(l) / 60)}:${String(Number(l) % 60).padStart(2, "0")}`}
                    />
                    <ReferenceLine y={50} stroke="#fbbf24" strokeDasharray="4 4" label={{ value: "50%", fontSize: 10 }} />
                    <Area type="monotone" dataKey="retention" stroke="#ef4444" fill="url(#retentionGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[240px] flex items-center justify-center text-muted-foreground text-sm">
                  Brak danych retencji
                </div>
              )}
            </div>

            {/* Drop Points */}
            <div className="bg-card border border-border rounded-lg p-4">
              <h2 className="font-semibold mb-3">Drop Points — Forensics</h2>
              {dropPoints.length > 0 ? (
                <div className="space-y-2 mb-4">
                  {dropPoints.slice(0, 5).map((dp, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-2 p-2.5 rounded-lg border text-xs bg-yellow-500/10 border-yellow-500/20"
                    >
                      <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-mono font-bold">
                          {Math.floor(dp.time / 60)}:{String(dp.time % 60).padStart(2, "0")}
                        </span>
                        <span className="text-muted-foreground mx-1.5">—</span>
                        <span>{dp.dropReason ?? "Spadek retencji"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg mb-4">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <p className="text-xs font-medium text-green-700">Brak krytycznych drop pointów</p>
                  </div>
                </div>
              )}

              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                <p className="text-xs font-medium text-blue-700 mb-1">Metryki:</p>
                <ul className="text-xs text-blue-600 space-y-0.5">
                  <li>• Czas oglądania: {Math.round(analytics.watchTimeMinutes)} min</li>
                  <li>• Polubienia: {formatNumber(analytics.likes)}</li>
                  <li>• Komentarze: {formatNumber(analytics.comments)}</li>
                  <li>• Przychody: ${analytics.revenue.toFixed(2)} (RPM: ${analytics.rpm.toFixed(2)})</li>
                </ul>
              </div>
            </div>
          </div>
        </>
      )}

      {!analyticsLoading && !analytics && activeVideo && (
        <div className="bg-card border border-border rounded-lg p-8 text-center text-muted-foreground">
          <p className="text-sm">Brak danych analitycznych dla tego filmu.</p>
          <p className="text-xs mt-1">Dane będą dostępne po uruchomieniu agenta Watch-Time Forensics.</p>
        </div>
      )}
    </div>
  );
}
