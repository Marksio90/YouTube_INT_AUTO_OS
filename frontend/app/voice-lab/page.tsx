"use client";
import { Construction } from "lucide-react";

export default function Page() {
  const titles: Record<string, string> = {
    "channel-architect": "Channel Architect",
    "voice-lab": "Voice Lab",
    "thumbnail-workshop": "Thumbnail Workshop",
    "video-assembly": "Video Assembly Studio",
    "seo-command": "SEO Command Center",
    "experiment-hub": "Experiment Hub",
  };
  const slug = "voice-lab";
  return (
    <div className="p-6 flex flex-col items-center justify-center min-h-[60vh] text-center">
      <Construction className="w-12 h-12 text-muted-foreground/30 mb-4" />
      <h1 className="text-2xl font-bold mb-2">{titles[slug]}</h1>
      <p className="text-muted-foreground text-sm max-w-md">
        Ten modul jest w trakcie implementacji. Bedzie dostepny w fazie PRO platformy.
      </p>
      <div className="mt-4 text-xs text-muted-foreground bg-muted px-3 py-2 rounded-lg">
        Roadmapa: MVP (M1-4) → PRO (M5-9) → COSMIC (M10-24)
      </div>
    </div>
  );
}
