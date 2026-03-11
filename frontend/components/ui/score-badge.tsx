import { cn, getScoreBg } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number;
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function ScoreBadge({ score, label, size = "md", className }: ScoreBadgeProps) {
  const colorClass = getScoreBg(score);
  const sizeClass = {
    sm: "text-xs px-1.5 py-0.5",
    md: "text-sm px-2 py-1",
    lg: "text-base px-3 py-1.5",
  }[size];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border font-medium",
        colorClass,
        sizeClass,
        className
      )}
    >
      {label && <span className="opacity-70">{label}:</span>}
      <span>{score}/100</span>
    </span>
  );
}
