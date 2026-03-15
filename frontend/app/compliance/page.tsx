"use client";

import { cn } from "@/lib/utils";
import { ScoreBadge } from "@/components/ui/score-badge";
import { Shield, AlertTriangle, CheckCircle, XCircle, Info, Loader2 } from "lucide-react";
import { useChannels } from "@/hooks/useApi";
import type { Channel } from "@/types";

const RISK_ICONS = {
  green: CheckCircle,
  yellow: AlertTriangle,
  red: XCircle,
};

const RISK_COLORS = {
  green: "text-green-500 bg-green-500/10 border-green-500/20",
  yellow: "text-yellow-500 bg-yellow-500/10 border-yellow-500/20",
  red: "text-red-500 bg-red-500/10 border-red-500/20",
};

function getRiskLevel(score: number): "green" | "yellow" | "red" {
  if (score >= 85) return "green";
  if (score >= 70) return "yellow";
  return "red";
}

export default function CompliancePage() {
  const { data: channels = [], isLoading } = useChannels();

  const qualityGates = [
    {
      name: "Wynik Oryginalności",
      threshold: "≥ 85/100",
      current: channels.length > 0
        ? Math.round(channels.reduce((s: number, c: Channel) => s + (c.originalityScore ?? 0), 0) / channels.length)
        : "—",
      passed: channels.length > 0 && channels.every((c: Channel) => (c.originalityScore ?? 0) >= 85),
    },
    {
      name: "Wynik Zgodności",
      threshold: "≥ 80/100",
      current: channels.length > 0
        ? Math.round(channels.reduce((s: number, c: Channel) => s + (c.complianceScore ?? 0), 0) / channels.length)
        : "—",
      passed: channels.length > 0 && channels.every((c: Channel) => (c.complianceScore ?? 0) >= 80),
    },
    {
      name: "Podobieństwo Między Filmami",
      threshold: "cosine < 0.85",
      current: "Sprawdź agenta",
      passed: true,
    },
    {
      name: "Ryzyko Praw Autorskich",
      threshold: "Zielony",
      current: "Zielony",
      passed: true,
    },
    {
      name: "Ujawnienie AI",
      threshold: "Ustawione dla synth. mediów",
      current: "Ustawione",
      passed: true,
    },
    {
      name: "Bezpieczeństwo Reklamodawcy YPP",
      threshold: "Tak",
      current: channels.some((c: Channel) => c.yppStatus === "active") ? "Tak" : "Sprawdź",
      passed: channels.some((c: Channel) => c.yppStatus === "active"),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="w-6 h-6 text-primary" />
            Compliance Center
          </h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Agenci: Oryginalność i Transformacja • Prawa i Ryzyko • Gotowość do Monetyzacji
          </p>
        </div>
        <button className="bg-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-primary/90">
          Uruchom pełny skan
        </button>
      </div>

      {/* YouTube Policy Warning */}
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
        <div className="flex gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-700">Polityka Inauthentic Content — Aktywna od 15.07.2025</p>
            <p className="text-xs text-red-600 mt-1 leading-relaxed">
              YouTube egzekwuje zakaz treści &quot;easily replicable at scale&quot; i template-driven content. Styczeń 2026: 16 kanałów usuniętych (4.7 mld wyświetleń).
              Kazdy film musi przejsc: Originality Score ≥ 85/100 oraz Similarity cosine &lt; 0.85.
            </p>
          </div>
        </div>
      </div>

      {/* Quality Gates */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h2 className="font-semibold mb-3">Quality Gates — Compliance Layer</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {qualityGates.map((gate) => (
            <div
              key={gate.name}
              className={cn(
                "flex items-center gap-2 p-3 rounded-lg border",
                gate.passed ? "bg-green-500/5 border-green-500/20" : "bg-red-500/5 border-red-500/20"
              )}
            >
              {gate.passed
                ? <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
                : <XCircle className="w-4 h-4 text-red-500 shrink-0" />
              }
              <div className="min-w-0">
                <p className="text-xs font-medium truncate">{gate.name}</p>
                <p className="text-xs text-muted-foreground">
                  Prog: {gate.threshold} | Wynik: <strong>{String(gate.current)}</strong>
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Channel Scorecard */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h2 className="font-semibold mb-3">Scorecard Kanałów</h2>
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Ładowanie kanałów...</span>
          </div>
        ) : channels.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">
            Brak kanalow. Dodaj kanal w ustawieniach.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 px-3 text-xs text-muted-foreground font-medium">Kanal</th>
                  <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">Oryginalność</th>
                  <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">Compliance</th>
                  <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">Ryzyko</th>
                  <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">YPP Status</th>
                </tr>
              </thead>
              <tbody>
                {channels.map((channel: Channel) => {
                  const riskLevel = getRiskLevel(channel.complianceScore ?? 0);
                  const RiskIcon = RISK_ICONS[riskLevel];
                  return (
                    <tr key={channel.id} className="border-b border-border/50 hover:bg-muted/30">
                      <td className="py-3 px-3 font-medium">{channel.name}</td>
                      <td className="py-3 px-3 text-center">
                        <ScoreBadge score={channel.originalityScore ?? 0} size="sm" />
                      </td>
                      <td className="py-3 px-3 text-center">
                        <ScoreBadge score={channel.complianceScore ?? 0} size="sm" />
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span className={cn("inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium", RISK_COLORS[riskLevel])}>
                          <RiskIcon className="w-3 h-3" />
                          {riskLevel.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span className={cn(
                          "text-xs px-2 py-0.5 rounded-full font-medium",
                          channel.yppStatus === "active"
                            ? "bg-green-500/10 text-green-600"
                            : channel.yppStatus === "pending"
                              ? "bg-yellow-500/10 text-yellow-600"
                              : "bg-muted text-muted-foreground"
                        )}>
                          {channel.yppStatus.replace("_", " ")}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info panel */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h2 className="font-semibold mb-3">Jak uruchomić pełny skan</h2>
        <div className="flex items-start gap-2 text-sm text-muted-foreground">
          <Info className="w-4 h-4 shrink-0 mt-0.5" />
          <p>
            Aby uzyskać szczegółowy raport compliance dla konkretnego filmu, przejdź do{" "}
            <strong>Content Pipeline</strong>, wybierz film i kliknij{" "}
            <strong>Uruchom compliance check</strong>. Agenci Originality &amp; Transformation
            oraz Rights &amp; Risk przeanalizują film i zapiszą raport.
          </p>
        </div>
      </div>
    </div>
  );
}
