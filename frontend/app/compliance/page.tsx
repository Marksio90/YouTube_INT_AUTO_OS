"use client";

import { cn } from "@/lib/utils";
import { ScoreBadge } from "@/components/ui/score-badge";
import { Shield, AlertTriangle, CheckCircle, XCircle, Info } from "lucide-react";

const mockComplianceData = {
  channels: [
    { name: "AI Finanse PL", originalityScore: 87, complianceScore: 92, riskLevel: "green", issues: 1, disclosuresOk: true, yppSafe: true },
    { name: "Technologia Przyszlosci", originalityScore: 82, complianceScore: 88, riskLevel: "green", issues: 2, disclosuresOk: true, yppSafe: true },
    { name: "Edukacja Online", originalityScore: 91, complianceScore: 95, riskLevel: "green", issues: 0, disclosuresOk: true, yppSafe: true },
  ],
  recentIssues: [
    { severity: "yellow", category: "Similarity Risk", video: "5 Sekretow Inwestowania w ETF 2026", description: "Similarity score 0.87 z poprzednim filmem — powyiej progu 0.85", remediation: "Zmien 3 glowne argumenty lub zmien podejscie narracyjne", channel: "AI Finanse PL" },
    { severity: "yellow", category: "Template Overuse", video: "Seria 'Top 10'", description: "4 z 6 ostatnich filmow uzywa struktury 'Top N' — ryzyko template farm", remediation: "Nastepne 2 filmy uzyj innej struktury narracyjnej", channel: "Technologia Przyszlosci" },
    { severity: "green", category: "AI Disclosure", video: "ChatGPT vs Claude 2026", description: "Disclosure AI poprawnie ustawiony w opisie i metadata", remediation: "", channel: "Technologia Przyszlosci" },
  ],
  qualityGates: [
    { name: "Originality Score", threshold: "≥ 85/100", current: 87, passed: true },
    { name: "Template Overuse", threshold: "≤ 2/5 podobnych", current: "1/5", passed: true },
    { name: "Cross-video Similarity", threshold: "cosine < 0.85", current: 0.81, passed: true },
    { name: "Copyright Risk", threshold: "Green", current: "Green", passed: true },
    { name: "AI Disclosure", threshold: "Set dla synth. media", current: "Set", passed: true },
    { name: "YPP Advertiser Safe", threshold: "Tak", current: "Tak", passed: true },
  ],
};

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

export default function CompliancePage() {
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
            Agenci: Originality & Transformation • Rights & Risk • Monetization Readiness
          </p>
        </div>
        <button className="bg-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-primary/90">
          Uruchom pelen skan
        </button>
      </div>

      {/* YouTube Policy Warning */}
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
        <div className="flex gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-700">Polityka Inauthentic Content — Aktywna od 15.07.2025</p>
            <p className="text-xs text-red-600 mt-1 leading-relaxed">
              YouTube egzekwuje zakaz tresci &quot;easily replicable at scale&quot; i template-driven content. Styczen 2026: 16 kanalow usunieto (4.7 mld wyswietlen).
              Kazdy film musi przejsc: Originality Score ≥ 85/100 oraz Similarity cosine &lt; 0.85.
            </p>
          </div>
        </div>
      </div>

      {/* Quality Gates */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h2 className="font-semibold mb-3">Quality Gates — Compliance Layer</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {mockComplianceData.qualityGates.map((gate) => (
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
        <h2 className="font-semibold mb-3">Scorecard Kanalow</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-3 text-xs text-muted-foreground font-medium">Kanal</th>
                <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">Oryginalnosc</th>
                <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">Compliance</th>
                <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">Ryzyko</th>
                <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">Disclosure</th>
                <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">YPP Safe</th>
                <th className="text-center py-2 px-3 text-xs text-muted-foreground font-medium">Issues</th>
              </tr>
            </thead>
            <tbody>
              {mockComplianceData.channels.map((channel) => {
                const RiskIcon = RISK_ICONS[channel.riskLevel as keyof typeof RISK_ICONS];
                return (
                  <tr key={channel.name} className="border-b border-border/50 hover:bg-muted/30">
                    <td className="py-3 px-3 font-medium">{channel.name}</td>
                    <td className="py-3 px-3 text-center">
                      <ScoreBadge score={channel.originalityScore} size="sm" />
                    </td>
                    <td className="py-3 px-3 text-center">
                      <ScoreBadge score={channel.complianceScore} size="sm" />
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={cn("inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium", RISK_COLORS[channel.riskLevel as keyof typeof RISK_COLORS])}>
                        <RiskIcon className="w-3 h-3" />
                        {channel.riskLevel.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      {channel.disclosuresOk
                        ? <CheckCircle className="w-4 h-4 text-green-500 mx-auto" />
                        : <XCircle className="w-4 h-4 text-red-500 mx-auto" />
                      }
                    </td>
                    <td className="py-3 px-3 text-center">
                      {channel.yppSafe
                        ? <CheckCircle className="w-4 h-4 text-green-500 mx-auto" />
                        : <XCircle className="w-4 h-4 text-red-500 mx-auto" />
                      }
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={cn(
                        "text-xs font-medium px-2 py-0.5 rounded-full",
                        channel.issues === 0 ? "bg-green-500/10 text-green-600" : "bg-yellow-500/10 text-yellow-600"
                      )}>
                        {channel.issues}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Issues */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h2 className="font-semibold mb-3">Aktywne Issues i Remediation</h2>
        <div className="space-y-3">
          {mockComplianceData.recentIssues.map((issue, i) => {
            const Icon = RISK_ICONS[issue.severity as keyof typeof RISK_ICONS];
            return (
              <div
                key={i}
                className={cn(
                  "p-3 rounded-lg border",
                  RISK_COLORS[issue.severity as keyof typeof RISK_COLORS]
                )}
              >
                <div className="flex items-start gap-2">
                  <Icon className="w-4 h-4 shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                      <span className="text-xs font-semibold">{issue.category}</span>
                      <span className="text-xs opacity-70">•</span>
                      <span className="text-xs opacity-70">{issue.channel}</span>
                      <span className="text-xs opacity-70">•</span>
                      <span className="text-xs opacity-70 italic">{issue.video}</span>
                    </div>
                    <p className="text-xs">{issue.description}</p>
                    {issue.remediation && (
                      <div className="flex items-start gap-1 mt-1.5">
                        <Info className="w-3 h-3 shrink-0 mt-0.5 opacity-70" />
                        <p className="text-xs opacity-80">
                          <strong>Remediation:</strong> {issue.remediation}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
