"use client";

import { useState } from "react";
import { cn, getScoreColor } from "@/lib/utils";
import { ScoreBadge } from "@/components/ui/score-badge";
import { Zap, RefreshCw, ChevronRight, AlertCircle, CheckCircle, Lightbulb, Loader2 } from "lucide-react";
import { useVideos, useScript, useGenerateScript } from "@/hooks/useApi";
import type { VideoProject } from "@/types";

const SCRIPT_SECTIONS = [
  { key: "hook", label: "Hook (0-30s)", description: "Pierwsze zdanie zatrzymujace kciuk", required: true },
  { key: "intro", label: "Intro (30s-2min)", description: "Obietnica wartosci + setup napięcia", required: true },
  { key: "problem", label: "Problem (2-5min)", description: "Glebokie zanurzenie w problem widza", required: true },
  { key: "deepening", label: "Deepening (5-10min)", description: "Rozszerzenie problemu, dane, historia", required: true },
  { key: "value", label: "Value (10-18min)", description: "Glowna wartosc, rozwiazanie, insights", required: true },
  { key: "cta", label: "CTA (ostatnie 60s)", description: "Wezwanie do akcji + tease kolejnego filmu", required: true },
];

export default function ScriptStudioPage() {
  const [activeSection, setActiveSection] = useState("hook");
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);

  // Videos in "script" stage have active scripts
  const { data: allVideos = [], isLoading: videosLoading } = useVideos(undefined, "script");
  const selectedVideo = allVideos.find((v: VideoProject) => v.id === selectedVideoId) ?? allVideos[0] ?? null;
  const scriptId = selectedVideo?.scriptId ?? null;

  const { data: script, isLoading: scriptLoading } = useScript(scriptId ?? "");
  const generateScript = useGenerateScript();

  const isLoading = videosLoading || scriptLoading;

  const scriptContent: Record<string, string> = script
    ? {
        hook: script.hook ?? "",
        intro: script.intro ?? "",
        problem: script.problem ?? "",
        deepening: script.deepening ?? "",
        value: script.value ?? "",
        cta: script.cta ?? "",
      }
    : {};

  const hookScore = script?.hookScore ?? 0;
  const naturalityScore = script?.naturalityScore ?? 0;
  const originalityScore = script?.originalityScore ?? 0;
  const retentionScore = script?.retentionScore ?? 0;
  const qualityGatePassed = hookScore >= 8 && originalityScore >= 85;

  return (
    <div className="p-6 h-full flex flex-col gap-4">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold">Script Studio</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Agenci: Script Strategist • Hook Specialist • Retention Editor
          </p>
        </div>
        <div className="flex gap-2">
          {/* Video selector */}
          {allVideos.length > 0 && (
            <select
              value={selectedVideoId ?? selectedVideo?.id ?? ""}
              onChange={(e) => setSelectedVideoId(e.target.value)}
              className="text-sm px-3 py-2 border border-border rounded-lg bg-muted focus:outline-none focus:ring-1 focus:ring-primary max-w-[220px] truncate"
            >
              {allVideos.map((v: VideoProject) => (
                <option key={v.id} value={v.id}>{v.title}</option>
              ))}
            </select>
          )}
          <button className="text-sm px-3 py-2 border border-border rounded-lg hover:bg-muted flex items-center gap-1.5">
            <RefreshCw className="w-4 h-4" />
            Regeneruj
          </button>
          <button className="bg-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-primary/90 flex items-center gap-1.5">
            <Zap className="w-4 h-4" />
            Generuj Voice-Over
          </button>
        </div>
      </div>

      {/* Quality Scores Bar */}
      {script && (
        <div className="flex gap-3 p-3 bg-card border border-border rounded-lg shrink-0">
          {[
            { label: "Hook Score", value: hookScore, outOf: 10, good: 8 },
            { label: "Naturalnosc", value: naturalityScore, outOf: 10, good: 8 },
          ].map((s) => (
            <div key={s.label} className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">{s.label}:</span>
              <span className={cn("text-sm font-bold", s.value >= s.good ? "text-green-500" : "text-yellow-500")}>
                {s.value}/{s.outOf}
              </span>
              {s.value >= s.good
                ? <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                : <AlertCircle className="w-3.5 h-3.5 text-yellow-500" />
              }
            </div>
          ))}
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Oryginalnosc:</span>
            <ScoreBadge score={originalityScore} size="sm" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Retencja:</span>
            <ScoreBadge score={retentionScore} size="sm" />
          </div>
          <div className={cn("ml-auto text-xs font-medium flex items-center gap-1", qualityGatePassed ? "text-green-600" : "text-yellow-600")}>
            {qualityGatePassed
              ? <><CheckCircle className="w-3.5 h-3.5" />Quality Gate PASSED</>
              : <><AlertCircle className="w-3.5 h-3.5" />Quality Gate PENDING</>
            }
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center flex-1 text-muted-foreground gap-2">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Ladowanie skryptu...</span>
        </div>
      ) : !selectedVideo ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <p className="text-lg font-medium mb-2">Brak projektow w etapie Script</p>
            <p className="text-sm">Przejdz do Content Pipeline i rozpocznij nowy projekt</p>
          </div>
        </div>
      ) : !script ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <p className="text-lg font-medium mb-2">Brak skryptu dla tego projektu</p>
            <button
              onClick={() => generateScript.mutate({
                video_project_id: selectedVideo.id,
                topic: selectedVideo.title,
                target_keywords: selectedVideo.targetKeywords,
              })}
              disabled={generateScript.isPending}
              className="mt-3 bg-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-primary/90 flex items-center gap-2 mx-auto disabled:opacity-50"
            >
              {generateScript.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              <Zap className="w-4 h-4" />
              Generuj skrypt
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4 flex-1 min-h-0">
          {/* Left: Section Navigator */}
          <div className="flex flex-col gap-2">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Struktura 6-czesciowa
            </p>
            {SCRIPT_SECTIONS.map((section) => (
              <button
                key={section.key}
                onClick={() => setActiveSection(section.key)}
                className={cn(
                  "text-left px-3 py-2.5 rounded-lg border transition-colors",
                  activeSection === section.key
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/30"
                )}
              >
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-sm font-medium">{section.label}</span>
                  <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
                </div>
                <p className="text-xs text-muted-foreground">{section.description}</p>
              </button>
            ))}
          </div>

          {/* Center: Editor */}
          <div className="flex flex-col gap-3 overflow-y-auto">
            <div className="bg-card border border-border rounded-lg p-4 flex-1">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-sm">
                  {SCRIPT_SECTIONS.find((s) => s.key === activeSection)?.label}
                </h3>
                <button className="text-xs text-primary hover:underline flex items-center gap-1">
                  <RefreshCw className="w-3 h-3" />
                  Regeneruj sekcje
                </button>
              </div>
              <textarea
                className="w-full h-80 text-sm bg-transparent resize-none focus:outline-none leading-relaxed"
                value={scriptContent[activeSection] ?? ""}
                readOnly
              />
            </div>

            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle className="w-3.5 h-3.5 text-green-600" />
                <span className="text-xs font-medium text-green-700">
                  {script.estimatedDurationSeconds
                    ? `Szacowany czas: ${Math.round(script.estimatedDurationSeconds / 60)} min`
                    : "Retention resets co ~75 sekund"}
                </span>
              </div>
              <p className="text-xs text-green-600">{script.wordCount} slow • wersja {script.version}</p>
            </div>
          </div>

          {/* Right: AI Suggestions */}
          <div className="flex flex-col gap-3 overflow-y-auto">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Analiza skryptu
            </p>
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <Lightbulb className="w-3.5 h-3.5 text-blue-600" />
                <span className="text-xs font-medium text-blue-700">Retention Editor: Sugestie</span>
              </div>
              <ul className="space-y-1.5 text-xs text-blue-600">
                {retentionScore < 80 && <li>• Dodaj micro-payoff co 75 sekund</li>}
                {hookScore < 8 && <li>• Wzmocnij hook — aktualny score: {hookScore}/10</li>}
                {originalityScore < 85 && <li>• Zwieksz oryginalnosc — aktualny score: {originalityScore}/100</li>}
                {hookScore >= 8 && retentionScore >= 80 && originalityScore >= 85 && (
                  <li>• Skrypt spelnia wszystkie quality gates</li>
                )}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
