"use client";

import { useState } from "react";
import { ScoreBadge } from "@/components/ui/score-badge";
import { cn } from "@/lib/utils";
import { Search, TrendingUp, TrendingDown, Minus, Star, Loader2, AlertCircle } from "lucide-react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ZAxis,
} from "recharts";
import { useNicheAnalyses, useRunNicheAnalysis } from "@/hooks/useApi";
import type { NicheScore } from "@/types";

export default function NicheExplorerPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showAnalyzeForm, setShowAnalyzeForm] = useState(false);
  const [newNicheName, setNewNicheName] = useState("");
  const [newNicheCategory, setNewNicheCategory] = useState("");

  const { data: niches = [], isLoading, error } = useNicheAnalyses();
  const runAnalysis = useRunNicheAnalysis();

  const filtered = niches.filter(
    (n) =>
      n.name.toLowerCase().includes(search.toLowerCase()) ||
      (n.category ?? "").toLowerCase().includes(search.toLowerCase())
  );

  const selectedNiche = niches.find((n) => n.id === selected);

  const scatterData = niches.map((n) => ({
    x: n.demandScore,
    y: n.estimatedMonthlyRpm ?? 0,
    z: 100 - n.productionDifficulty,
    name: n.name,
    score: n.overallScore,
    id: n.id,
  }));

  function handleAnalyze() {
    if (!newNicheName.trim()) return;
    runAnalysis.mutate(
      { niche_name: newNicheName.trim(), category: newNicheCategory.trim() || undefined },
      {
        onSuccess: () => {
          setShowAnalyzeForm(false);
          setNewNicheName("");
          setNewNicheCategory("");
        },
      }
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Niche Explorer</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Agent: Niche Hunter • Opportunity Mapper • Competitive Deconstruction
          </p>
        </div>
        <button
          onClick={() => setShowAnalyzeForm(!showAnalyzeForm)}
          className="bg-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors"
        >
          + Analizuj nowa nisza
        </button>
      </div>

      {/* New analysis form */}
      {showAnalyzeForm && (
        <div className="bg-card border border-border rounded-lg p-4 flex gap-3 items-end">
          <div className="flex-1">
            <label className="text-xs text-muted-foreground mb-1 block">Nazwa niszy *</label>
            <input
              type="text"
              placeholder="np. Finanse osobiste PL"
              value={newNicheName}
              onChange={(e) => setNewNicheName(e.target.value)}
              className="w-full px-3 py-1.5 text-sm bg-muted border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="w-44">
            <label className="text-xs text-muted-foreground mb-1 block">Kategoria</label>
            <input
              type="text"
              placeholder="np. Finanse"
              value={newNicheCategory}
              onChange={(e) => setNewNicheCategory(e.target.value)}
              className="w-full px-3 py-1.5 text-sm bg-muted border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <button
            onClick={handleAnalyze}
            disabled={runAnalysis.isPending || !newNicheName.trim()}
            className="bg-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
          >
            {runAnalysis.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            Uruchom analize
          </button>
        </div>
      )}

      {/* Quality Gate Banner */}
      <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 flex items-center gap-2">
        <Star className="w-4 h-4 text-yellow-600 shrink-0" />
        <p className="text-sm text-yellow-700">
          <strong>Quality Gate:</strong> Niche Score &gt; 70/100 wymagany do przejscia do Channel Architect
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12 text-muted-foreground gap-2">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Ladowanie analiz nisz...</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-700 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          Blad ladowania nisz. Sprawdz polaczenie z API.
        </div>
      )}

      {!isLoading && !error && (
        <>
          <div className="grid grid-cols-3 gap-6">
            <div className="col-span-2 bg-card border border-border rounded-lg p-4">
              <h2 className="font-semibold mb-1">Mapa Nisz</h2>
              <p className="text-xs text-muted-foreground mb-3">
                Os X: Popyt | Os Y: RPM ($) | Rozmiar: Latwose produkcji
              </p>
              {niches.length === 0 ? (
                <div className="h-[280px] flex items-center justify-center text-muted-foreground text-sm">
                  Brak danych — uruchom analize niszy powyzej
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="x" name="Popyt" domain={[0, 100]} tick={{ fontSize: 11 }} label={{ value: "Popyt", position: "bottom", fontSize: 11 }} />
                    <YAxis dataKey="y" name="RPM ($)" tick={{ fontSize: 11 }} label={{ value: "RPM ($)", angle: -90, position: "left", fontSize: 11 }} />
                    <ZAxis dataKey="z" range={[50, 300]} />
                    <Tooltip
                      content={({ payload }) => {
                        if (!payload?.length) return null;
                        const d = payload[0].payload;
                        return (
                          <div className="bg-card border border-border rounded-lg p-2 text-xs shadow">
                            <p className="font-semibold">{d.name}</p>
                            <p>Popyt: {d.x} | RPM: ${d.y}</p>
                            <p>Score: {d.score}/100</p>
                          </div>
                        );
                      }}
                    />
                    <Scatter data={scatterData} fill="#ef4444" opacity={0.8} />
                  </ScatterChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="bg-card border border-border rounded-lg p-4">
              {selectedNiche ? (
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold">{selectedNiche.name}</h3>
                      <p className="text-xs text-muted-foreground">{selectedNiche.category}</p>
                    </div>
                    <ScoreBadge score={selectedNiche.overallScore} />
                  </div>

                  <div className="space-y-2">
                    {[
                      { label: "Popyt", value: selectedNiche.demandScore },
                      { label: "Konkurencja (odw.)", value: selectedNiche.competitionScore },
                      { label: "RPM Potential", value: Math.min(selectedNiche.rpmPotential * 6, 100) },
                      { label: "Sponsor Fit", value: selectedNiche.sponsorPotential },
                    ].map((item) => (
                      <div key={item.label}>
                        <div className="flex justify-between text-xs mb-0.5">
                          <span className="text-muted-foreground">{item.label}</span>
                          <span className="font-medium">{Math.round(item.value)}/100</span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-1.5">
                          <div className="bg-primary h-1.5 rounded-full" style={{ width: `${Math.min(item.value, 100)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>

                  {(selectedNiche.contentGaps ?? []).length > 0 && (
                    <div className="pt-2 border-t border-border">
                      <p className="text-xs font-medium mb-1">Luki Contentowe:</p>
                      <div className="space-y-1">
                        {selectedNiche.contentGaps.map((gap) => (
                          <div key={gap} className="text-xs bg-green-500/10 text-green-700 px-2 py-1 rounded">
                            {gap}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="pt-2 border-t border-border">
                    <p className="text-xs text-muted-foreground">
                      Est. RPM: <strong className="text-foreground">${selectedNiche.estimatedMonthlyRpm ?? "—"}/1000 wysw.</strong>
                    </p>
                  </div>

                  <button className="w-full bg-primary text-white text-xs py-2 rounded-lg hover:bg-primary/90">
                    Generuj Channel Blueprint →
                  </button>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-center">
                  <div className="text-muted-foreground">
                    <Search className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">Wybierz nisza z listy aby zobaczyc szczegoly</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-3 mb-4">
              <h2 className="font-semibold flex-1">Ranking Nisz ({filtered.length})</h2>
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Szukaj niszy..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-8 pr-3 py-1.5 text-sm bg-muted border border-border rounded-lg w-48 focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>
            {filtered.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">
                {niches.length === 0
                  ? "Brak analiz — kliknij '+ Analizuj nowa nisza' aby rozpoczac"
                  : "Brak wynikow dla podanej frazy"}
              </p>
            ) : (
              <div className="space-y-2">
                {filtered.map((niche: NicheScore, i) => (
                  <div
                    key={niche.id}
                    onClick={() => setSelected(niche.id === selected ? null : niche.id)}
                    className={cn(
                      "flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                      selected === niche.id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/30 hover:bg-muted/30"
                    )}
                  >
                    <span className="text-sm font-bold text-muted-foreground w-5">{i + 1}</span>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{niche.name}</p>
                      <p className="text-xs text-muted-foreground">{niche.category}</p>
                    </div>
                    <ScoreBadge score={niche.overallScore} size="sm" />
                    <span className="text-xs text-muted-foreground w-16 text-right">
                      RPM ~${niche.estimatedMonthlyRpm ?? "—"}
                    </span>
                    <div className="w-16">
                      {niche.trendDirection === "up" && <TrendingUp className="w-4 h-4 text-green-500 ml-auto" />}
                      {niche.trendDirection === "down" && <TrendingDown className="w-4 h-4 text-red-500 ml-auto" />}
                      {niche.trendDirection === "stable" && <Minus className="w-4 h-4 text-muted-foreground ml-auto" />}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
