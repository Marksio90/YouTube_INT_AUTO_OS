"use client";

import { useState } from "react";
import { ScoreBadge } from "@/components/ui/score-badge";
import { cn, formatCurrency } from "@/lib/utils";
import { Search, TrendingUp, TrendingDown, Minus, Star } from "lucide-react";
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

const mockNiches = [
  {
    id: "1", name: "Finanse osobiste PL", category: "Finanse",
    overallScore: 91, demandScore: 88, competitionScore: 72, rpmPotential: 14,
    productionDifficulty: 45, sponsorPotential: 95, seasonality: "evergreen",
    trendDirection: "up", estimatedMonthlyRpm: 13.5,
    topCompetitors: ["Stockbroker PL", "Finanse Osobiste TV"],
    contentGaps: ["AI w inwestowaniu", "ETF dla poczatkujacych", "Podatki kryptowalut 2026"],
  },
  {
    id: "2", name: "Narzedzia AI dla freelancerow", category: "AI & Tech",
    overallScore: 88, demandScore: 92, competitionScore: 58, rpmPotential: 11,
    productionDifficulty: 35, sponsorPotential: 88, seasonality: "evergreen",
    trendDirection: "up", estimatedMonthlyRpm: 9.8,
    topCompetitors: ["AI Tools Review", "Tech Insider PL"],
    contentGaps: ["Automatyzacja z AI Agents", "AI dla grafika", "Make vs n8n"],
  },
  {
    id: "3", name: "Nauka jezykow z AI", category: "Edukacja",
    overallScore: 84, demandScore: 85, competitionScore: 65, rpmPotential: 10,
    productionDifficulty: 30, sponsorPotential: 80, seasonality: "evergreen",
    trendDirection: "stable", estimatedMonthlyRpm: 9.2,
    topCompetitors: ["PolyglotPL", "JezykiAI"],
    contentGaps: ["Angielski z ChatGPT", "Japoński B2 w 6 miesiecy"],
  },
  {
    id: "4", name: "Psychologia sukcesu", category: "Rozwoj osobisty",
    overallScore: 79, demandScore: 82, competitionScore: 48, rpmPotential: 9,
    productionDifficulty: 25, sponsorPotential: 75, seasonality: "evergreen",
    trendDirection: "stable", estimatedMonthlyRpm: 8.4,
    topCompetitors: ["Mindset PL", "Motywacja TV"],
    contentGaps: ["Nawyki miliarderow", "Discipline over motivation"],
  },
  {
    id: "5", name: "Smart home & automatyzacja", category: "Technologia",
    overallScore: 76, demandScore: 78, competitionScore: 55, rpmPotential: 8,
    productionDifficulty: 55, sponsorPotential: 85, seasonality: "evergreen",
    trendDirection: "up", estimatedMonthlyRpm: 7.8,
    topCompetitors: ["SmartHomePL", "TechReview24"],
    contentGaps: ["Home Assistant vs Alexa", "Matter protocol 2026"],
  },
  {
    id: "6", name: "Zdrowie i biohacking", category: "Zdrowie",
    overallScore: 73, demandScore: 76, competitionScore: 62, rpmPotential: 8,
    productionDifficulty: 40, sponsorPotential: 90, seasonality: "seasonal",
    trendDirection: "up", estimatedMonthlyRpm: 7.2,
    topCompetitors: ["Biohacker PL", "Zdrowie i Forma"],
    contentGaps: ["Metformina longevity", "Peptidy 2026", "CGM dla nie-diabetykow"],
  },
];

const scatterData = mockNiches.map((n) => ({
  x: n.demandScore,
  y: n.estimatedMonthlyRpm,
  z: 100 - n.productionDifficulty,
  name: n.name,
  score: n.overallScore,
}));

export default function NicheExplorerPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const filtered = mockNiches.filter(
    (n) =>
      n.name.toLowerCase().includes(search.toLowerCase()) ||
      n.category.toLowerCase().includes(search.toLowerCase())
  );

  const selectedNiche = mockNiches.find((n) => n.id === selected);

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
        <button className="bg-primary text-white text-sm px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors">
          + Analizuj nowa nisza
        </button>
      </div>

      {/* Quality Gate Banner */}
      <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 flex items-center gap-2">
        <Star className="w-4 h-4 text-yellow-600 shrink-0" />
        <p className="text-sm text-yellow-700">
          <strong>Quality Gate:</strong> Niche Score &gt; 70/100 wymagany do przejscia do Channel Architect
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Scatter Chart */}
        <div className="col-span-2 bg-card border border-border rounded-lg p-4">
          <h2 className="font-semibold mb-1">Mapa Nisz</h2>
          <p className="text-xs text-muted-foreground mb-3">
            Os X: Popyt | Os Y: RPM ($) | Rozmiar: Latwose produkcji
          </p>
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="x" name="Popyt" domain={[60, 100]} tick={{ fontSize: 11 }} label={{ value: "Popyt", position: "bottom", fontSize: 11 }} />
              <YAxis dataKey="y" name="RPM ($)" domain={[6, 16]} tick={{ fontSize: 11 }} label={{ value: "RPM ($)", angle: -90, position: "left", fontSize: 11 }} />
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
        </div>

        {/* Detail Panel */}
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
                  { label: "RPM Potential", value: selectedNiche.rpmPotential * 6 },
                  { label: "Sponsor Fit", value: selectedNiche.sponsorPotential },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="text-muted-foreground">{item.label}</span>
                      <span className="font-medium">{item.value}/100</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-1.5">
                      <div
                        className="bg-primary h-1.5 rounded-full"
                        style={{ width: `${item.value}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>

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

              <div className="pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground">
                  Est. RPM: <strong className="text-foreground">${selectedNiche.estimatedMonthlyRpm}/1000 wysw.</strong>
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

      {/* Niche List */}
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="flex items-center gap-3 mb-4">
          <h2 className="font-semibold flex-1">Ranking Nisz</h2>
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
        <div className="space-y-2">
          {filtered.map((niche, i) => (
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
                RPM ~${niche.estimatedMonthlyRpm}
              </span>
              <div className="w-16">
                {niche.trendDirection === "up" && <TrendingUp className="w-4 h-4 text-green-500 ml-auto" />}
                {niche.trendDirection === "down" && <TrendingDown className="w-4 h-4 text-red-500 ml-auto" />}
                {niche.trendDirection === "stable" && <Minus className="w-4 h-4 text-muted-foreground ml-auto" />}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
