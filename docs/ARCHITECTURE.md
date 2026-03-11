# YouTube Intelligence & Automation OS — Architektura

## Przeglad Systemu

```
┌─────────────────────────────────────────────────────────────────┐
│                  YouTube INT & Automation OS                     │
│                  AI-Native Operating System                       │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│   FRONTEND (Next.js 15 + TypeScript + Tailwind + shadcn/ui)     │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│   │Dashboard │ │Niche     │ │Content   │ │Script            │  │
│   │         │ │Explorer  │ │Pipeline  │ │Studio            │  │
│   └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│   │Analytics │ │Experiment│ │SEO Cmd   │ │Compliance        │  │
│   │Forensics │ │Hub       │ │Center    │ │Center            │  │
│   └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │ REST API / TanStack Query
          ▼
┌─────────────────────────────────────────────────────────────────┐
│   BACKEND (FastAPI + Pydantic v2)                               │
│   /api/v1/channels   /api/v1/videos   /api/v1/agents            │
│   /api/v1/scripts    /api/v1/dashboard                          │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│   AGENT ORCHESTRATION (LangGraph 0.2+)                          │
│                                                                  │
│   Layer 1 - Market Intelligence                                  │
│   ┌────────────────┐ ┌──────────────────┐ ┌─────────────────┐  │
│   │ Niche Hunter   │ │Opportunity Mapper│ │Competitive      │  │
│   │ Score > 70     │ │Topic Map 50+     │ │Deconstruction   │  │
│   └────────────────┘ └──────────────────┘ └─────────────────┘  │
│                                                                  │
│   Layer 2 - Content Design                                       │
│   ┌────────────────┐ ┌──────────────────┐ ┌─────────────────┐  │
│   │Channel         │ │Script Strategist │ │Voice Persona    │  │
│   │Architect       │ │Hook > 8/10       │ │Brand Fit > 8    │  │
│   └────────────────┘ └──────────────────┘ └─────────────────┘  │
│                                                                  │
│   Layer 3 - AI Production (10 agents)                           │
│   Hook Specialist | Retention Editor | Thumbnail Psychology      │
│   Title Architect | Storyboard | Format Localizer                │
│   Asset Retrieval | Video Assembly (FFmpeg) | Audio Polish        │
│   Caption & Accessibility                                         │
│                                                                  │
│   Layer 4 - Optimization (3 agents)                              │
│   SEO Intelligence | Experimentation | Watch-Time Forensics       │
│                                                                  │
│   Layer 5 - Compliance (4 agents) ← KRYTYCZNE 2026              │
│   Channel Portfolio | Originality & Transformation               │
│   Rights & Risk | Monetization Readiness                          │
│   Quality Gate: Originality > 85 | cosine < 0.85                 │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│   DATA LAYER                                                     │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │ PostgreSQL 16 + pgvector                                  │  │
│   │ - channels, video_projects, scripts, analytics            │  │
│   │ - agent_runs, niche_analyses, experiments                 │  │
│   │ - content_embedding vector(1536) — similarity search      │  │
│   │ - IVFFlat index (100 lists) — fast ANN search             │  │
│   └──────────────────────────────────────────────────────────┘  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │ Redis (Upstash / self-hosted)                             │  │
│   │ - Job queues (Celery MVP / Temporal PRO)                  │  │
│   │ - Session cache                                           │  │
│   │ - Rate limiting (YouTube API 10K units/day)               │  │
│   └──────────────────────────────────────────────────────────┘  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │ Cloudflare R2 (Object Storage)                            │  │
│   │ - Voice tracks, thumbnails, assembled videos              │  │
│   │ - Stock assets cache                                      │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│   EXTERNAL INTEGRATIONS                                          │
│   OpenAI (GPT-4o premium + mini fast) | Anthropic Claude         │
│   ElevenLabs TTS ($11/msc) | YouTube Data API v3                 │
│   Kling AI video gen ($0.029/s) | Runway Gen-4                   │
│   Whisper STT | Pexels/Pixabay/Storyblocks assets                │
│   Langfuse monitoring | Google Trends                            │
└─────────────────────────────────────────────────────────────────┘
```

## Quality Gates (Per Etap Pipeline)

| Etap | Warunek | Agent |
|------|---------|-------|
| Niche → Channel | Score ≥ 70/100 | Niche Hunter |
| Script → Voice | Hook ≥ 8/10, Naturalnosc ≥ 8/10 | Script Strategist |
| Voice → Video | Prosody ≥ 7/10, Brand Fit ≥ 8/10 | Voice Persona |
| Thumbnail → SEO | Clarity ≥ 8/10, CTR Hypothesis ≥ 7/10 | Thumbnail Psychology |
| SEO → Review | SEO Score ≥ 75/100 | SEO Intelligence |
| Review → Publish | Originality ≥ 85/100, Cosine < 0.85 | Originality & Transformation |

## Compliance Stack 2026

- **Polityka**: Inauthentic Content (od 15.07.2025)
- **Weryfikacja**: Originality & Transformation Agent co film
- **Vector search**: pgvector cosine similarity (threshold 0.85)
- **Template detection**: embedding clustering + phrase repetition
- **AI Disclosure**: automatyczne przy synthetic voice/video
- **Copyright**: Rights & Risk Agent przed uplodem
