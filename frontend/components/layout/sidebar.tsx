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
    group: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    ],
  },
  {
    group: "Layer 1 - Market Intelligence",
    items: [
      { href: "/niche-explorer", label: "Niche Explorer", icon: Search },
    ],
  },
  {
    group: "Layer 2 - Content Design",
    items: [
      { href: "/channel-architect", label: "Channel Architect", icon: Building2 },
    ],
  },
  {
    group: "Layer 3 - Production",
    items: [
      { href: "/content-pipeline", label: "Content Pipeline", icon: Kanban },
      { href: "/script-studio", label: "Script Studio", icon: FileText },
      { href: "/voice-lab", label: "Voice Lab", icon: Mic },
      { href: "/thumbnail-workshop", label: "Thumbnail Workshop", icon: Image },
      { href: "/video-assembly", label: "Video Assembly", icon: Film },
    ],
  },
  {
    group: "Layer 4 - Optimization",
    items: [
      { href: "/seo-command", label: "SEO Command Center", icon: BarChart2 },
      { href: "/experiment-hub", label: "Experiment Hub", icon: FlaskConical },
      { href: "/analytics", label: "Analytics & Forensics", icon: TrendingUp },
    ],
  },
  {
    group: "Layer 5 - Compliance",
    items: [
      { href: "/compliance", label: "Compliance Center", icon: Shield },
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
