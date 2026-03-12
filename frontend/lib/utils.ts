import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes — canonical shadcn/ui utility. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a number with commas: 1234567 → "1,234,567" */
export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

/** Compact number: 12345 → "12.3K", 1234567 → "1.2M" */
export function formatCompact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

/** Format seconds to human-readable duration: 720 → "12:00" */
export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** Format ISO date string to locale-friendly short format */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Format ISO date string to relative time: "2 hours ago" */
export function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return formatDate(iso);
}

/** Percentage with one decimal: 0.542 → "54.2%" */
export function formatPercent(ratio: number): string {
  return `${(ratio * 100).toFixed(1)}%`;
}

/** Score color class based on value and max */
export function scoreColor(value: number, max: number = 100): string {
  const pct = value / max;
  if (pct >= 0.8) return "text-green-500";
  if (pct >= 0.6) return "text-yellow-500";
  return "text-red-500";
}

/** Text color class for a 0-100 score */
export function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  return "text-red-500";
}

/** Background + border color class for a 0-100 score badge */
export function getScoreBg(score: number): string {
  if (score >= 80) return "bg-green-500/10 border-green-500/30 text-green-400";
  if (score >= 60) return "bg-yellow-500/10 border-yellow-500/30 text-yellow-400";
  return "bg-red-500/10 border-red-500/30 text-red-400";
}

/** Format a number as USD currency: 1234.5 → "$1,234.50" */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(amount);
}

/** Human-readable labels for each pipeline stage */
export const PIPELINE_STAGE_LABELS: Record<string, string> = {
  idea: "Idea",
  script: "Script",
  voice: "Voice",
  video: "Video",
  thumbnail: "Thumbnail",
  seo: "SEO",
  review: "Review",
  scheduled: "Scheduled",
  published: "Published",
};

/** Tailwind color classes for each pipeline stage */
export const PIPELINE_STAGE_COLORS: Record<string, string> = {
  idea: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  script: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  voice: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  video: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  thumbnail: "bg-pink-500/10 text-pink-400 border-pink-500/20",
  seo: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  review: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  scheduled: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  published: "bg-green-500/10 text-green-400 border-green-500/20",
};
