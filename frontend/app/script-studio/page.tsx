"use client";

import { useState } from "react";
import { cn, getScoreColor } from "@/lib/utils";
import { ScoreBadge } from "@/components/ui/score-badge";
import { Zap, RefreshCw, ChevronRight, AlertCircle, CheckCircle, Lightbulb } from "lucide-react";

const SCRIPT_SECTIONS = [
  { key: "hook", label: "Hook (0-30s)", description: "Pierwsze zdanie zatrzymujace kciuk", required: true },
  { key: "intro", label: "Intro (30s-2min)", description: "Obietnica wartosci + setup napięcia", required: true },
  { key: "problem", label: "Problem (2-5min)", description: "Glebokie zanurzenie w problem widza", required: true },
  { key: "deepening", label: "Deepening (5-10min)", description: "Rozszerzenie problemu, dane, historia", required: true },
  { key: "value", label: "Value (10-18min)", description: "Glowna wartosc, rozwiazanie, insights", required: true },
  { key: "cta", label: "CTA (ostatnie 60s)", description: "Wezwanie do akcji + tease kolejnego filmu", required: true },
];

const mockScript = {
  hook: "Wyobraz sobie: wkladasz 500 zl miesiecznie w ETF przez 20 lat. Kalkulator mowi: 520 000 zl. Ale... wiekszosc ludzi robi JEDEN blad, ktory redukuje te kwote do 180 000 zl. Dzisiaj pokaze ci dokladnie co to jest.",
  intro: "Czesc, mam na imie Marek i od 8 lat inwestuje wylacznie w ETF-y. W tym filmie omowimy 5 bledow, ktore kosztuja przecietnego Polaka srednio 340 000 zl zyciowych oszczednosci. Zostań do konca, bo bled numer 3 popelnia nawet 78% doswiadczonych inwestorow.",
  problem: "Zacznijmy od fundamentalnego nieporozumienia. Wiekszosc ludzi mysli, ze inwestowanie w ETF to prosta sprawa: kupujesz, czekasz, zarabiasz. I to jest prawda... ale tylko jesli unikasz tych 5 pulapek.\n\nPulapka numer 1: Wybor ETF na podstawie historycznych stopy zwrotu...",
  deepening: "Badanie Vanguard z 2024 roku pokazuje, ze inwestorzy, ktorzy samodzielnie przenosza srodki miedzy ETF-ami, zarabiaja o 1.5% rocznie mniej niz ci, ktorzy trzymaja sie strategii. Przy 20-letnim horyzoncie to róznica 180 000 zl na portfelu 500 000 zl...",
  value: "Oto 5 zasad, ktore stosuje kazdy madry inwestor ETF:\n\n1. Dollar-Cost Averaging z automatyzacja (nie recznym zakupem)\n2. Rebalancing maksymalnie raz do roku, NIGDY po duzych spadkach\n3. Wybieranie ETF tylko z historii 10+ lat (nie 3-5 lat)\n4. TER ponizej 0.30% (sredni koszt 0.45% zjada 40 000 zl na 20 latach)\n5. Inwestowanie przez IKE/IKZE dla ulgi podatkowej...",
  cta: "Jesli ten film byl pomocny, wcisnij like i subskrybuj – nowe filmy o ETF i inwestowaniu co tydzien. W nastepnym filmie pokaze ci dokladnie jak zbudowac portfel 3-ETF ktory bil SP500 przez 15 lat. Link w opisie. Do zobaczenia!",
};

const mockHooks = [
  { type: "Shock", text: "Wyobraz sobie: wkladasz 500 zl miesiecznie w ETF przez 20 lat. Kalkulator mowi: 520 000 zl. Ale... wiekszosc ludzi robi JEDEN blad, ktory redukuje te kwote do 180 000 zl.", score: 9.1 },
  { type: "Open Loop", text: "Mam znajomego, ktory przez 15 lat inwestowal w ETF. Zarobil 12 000 zl. Jego brat – ta sama strategia, ta sama kwota – zarobil 280 000 zl. Powiem ci dzisiaj co robil inaczej.", score: 8.8 },
  { type: "Contrarian", text: "Wieksosc poradnikow inwestycyjnych na YouTube jest niepoprawna. Nie dlatego, ze klamia – ale dlatego, ze pomijaja jeden kluczowy czynnik, ktory moze podwoic lub przepolowic twoje zyski.", score: 8.4 },
  { type: "Curiosity Gap", text: "Jest jeden wskaznik, na ktory 99% inwestorow ETF w Polsce nie zwraca uwagi. Banki go ukrywaja, influencerzy finansowi go ignoruja. A roznica miedzy ignorowaniem go a uwzglednieniem to srednio 180 000 zl.", score: 8.2 },
];

export default function ScriptStudioPage() {
  const [activeSection, setActiveSection] = useState("hook");
  const [selectedHook, setSelectedHook] = useState(0);

  const scores = { hook: 9.1, naturalnosc: 8.3, oryginalnosc: 84, retencja: 82, seo: 78 };

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
      <div className="flex gap-3 p-3 bg-card border border-border rounded-lg shrink-0">
        {[
          { label: "Hook Score", value: scores.hook, outOf: 10, good: 8 },
          { label: "Naturalnosc", value: scores.naturalnosc, outOf: 10, good: 8 },
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
          <ScoreBadge score={scores.oryginalnosc} size="sm" />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Retencja:</span>
          <ScoreBadge score={scores.retencja} size="sm" />
        </div>
        <div className="ml-auto text-xs text-green-600 font-medium flex items-center gap-1">
          <CheckCircle className="w-3.5 h-3.5" />
          Quality Gate PASSED
        </div>
      </div>

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
              value={mockScript[activeSection as keyof typeof mockScript] || ""}
              readOnly
            />
          </div>

          {/* Retention resets indicator */}
          <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="w-3.5 h-3.5 text-green-600" />
              <span className="text-xs font-medium text-green-700">Retention resets co ~75 sekund</span>
            </div>
            <p className="text-xs text-green-600">3 micro-payoffs wykryte • Brak martwych akapitow</p>
          </div>
        </div>

        {/* Right: Hook Variants */}
        <div className="flex flex-col gap-3 overflow-y-auto">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Hook Specialist — 4 warianty
          </p>
          {mockHooks.map((hook, i) => (
            <div
              key={i}
              onClick={() => setSelectedHook(i)}
              className={cn(
                "p-3 rounded-lg border cursor-pointer transition-colors",
                selectedHook === i
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/30"
              )}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium bg-muted px-1.5 py-0.5 rounded">{hook.type}</span>
                <span className={cn("text-sm font-bold", hook.score >= 8 ? "text-green-500" : "text-yellow-500")}>
                  {hook.score}/10
                </span>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground line-clamp-3">{hook.text}</p>
            </div>
          ))}

          {/* AI Suggestions */}
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Lightbulb className="w-3.5 h-3.5 text-blue-600" />
              <span className="text-xs font-medium text-blue-700">Retention Editor: Sugestie</span>
            </div>
            <ul className="space-y-1.5 text-xs text-blue-600">
              <li>• Skroc wprowadzenie z 45s do 30s</li>
              <li>• Dodaj "pattern interrupt" po minucie 7</li>
              <li>• CTA za wczesnie — przesun na ostatnie 45s</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
