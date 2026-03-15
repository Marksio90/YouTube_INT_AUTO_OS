"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Search,
  Building2,
  Kanban,
  FileText,
  Mic,
  Image,
  Film,
  BarChart2,
  FlaskConical,
  TrendingUp,
  Shield,
  ChevronRight,
  Zap,
} from "lucide-react";

const navItems = [
  {
    group: "Przegląd",
    items: [
      { href: "/dashboard", label: "Panel główny", icon: LayoutDashboard },
    ],
  },
  {
    group: "Warstwa 1 — Wywiad Rynkowy",
    items: [
      { href: "/niche-explorer", label: "Eksplorator Nisz", icon: Search },
    ],
  },
  {
    group: "Warstwa 2 — Projektowanie Treści",
    items: [
      { href: "/channel-architect", label: "Architekt Kanału", icon: Building2 },
    ],
  },
  {
    group: "Warstwa 3 — Produkcja",
    items: [
      { href: "/content-pipeline", label: "Pipeline Produkcji", icon: Kanban },
      { href: "/script-studio", label: "Studio Skryptów", icon: FileText },
      { href: "/voice-lab", label: "Laboratorium Głosu", icon: Mic },
      { href: "/thumbnail-workshop", label: "Warsztat Miniatur", icon: Image },
      { href: "/video-assembly", label: "Montaż Wideo", icon: Film },
    ],
  },
  {
    group: "Warstwa 4 — Optymalizacja",
    items: [
      { href: "/seo-command", label: "Centrum SEO", icon: BarChart2 },
      { href: "/experiment-hub", label: "Hub Eksperymentów", icon: FlaskConical },
      { href: "/analytics", label: "Analityka i Diagnostyka", icon: TrendingUp },
    ],
  },
  {
    group: "Warstwa 5 — Zgodność",
    items: [
      { href: "/compliance", label: "Centrum Zgodności", icon: Shield },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-card border-r border-border flex flex-col h-full shrink-0">
      {/* Logo */}
      <div className="p-4 border-b border-border">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-bold leading-tight text-foreground">YouTube INT</span>
            <span className="text-xs text-muted-foreground leading-tight">Automation OS</span>
          </div>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto p-2">
        {navItems.map((group) => (
          <div key={group.group} className="mb-4">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-2 mb-1">
              {group.group}
            </p>
            {group.items.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="flex-1">{item.label}</span>
                  {isActive && <ChevronRight className="w-3 h-3" />}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-border">
        <div className="text-xs text-muted-foreground text-center">
          <p className="font-medium">YouTube INT OS v1.0</p>
          <p>Marksio AI Solutions</p>
        </div>
      </div>
    </aside>
  );
}
