// ============================================================
// Core Domain Types
// ============================================================

export type AgentStatus = "idle" | "running" | "completed" | "error" | "paused";
export type RiskLevel = "green" | "yellow" | "red";
export type PipelineStage =
  | "idea"
  | "script"
  | "voice"
  | "video"
  | "thumbnail"
  | "seo"
  | "review"
  | "scheduled"
  | "published";
export type RevenueStream = "adsense" | "affiliate" | "sponsorship" | "digital_products" | "memberships";
export type ContentFormat = "long_form" | "shorts" | "podcast_video" | "clips" | "community_post";

// ============================================================
// Channel Types
// ============================================================

export interface Channel {
  id: string;
  name: string;
  niche: string;
  description: string;
  youtubeChannelId?: string;
  subscribers: number;
  totalViews: number;
  watchHours: number;
  monthlyRevenue: number;
  yppStatus: "not_eligible" | "pending" | "active" | "suspended";
  complianceScore: number;
  originalityScore: number;
  brandConsistencyScore: number;
  contentPillars: string[];
  thumbnailStyle: string;
  voicePersonaId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChannelKPI {
  channelId: string;
  subscribers: number;
  subscribersGrowth: number;
  views: number;
  viewsGrowth: number;
  watchHours: number;
  watchHoursGrowth: number;
  avgCTR: number;
  avgRetention: number;
  avgViewDuration: number;
  revenue: number;
  revenueGrowth: number;
  rpm: number;
  period: string;
}

// ============================================================
// Niche Types
// ============================================================

export interface NicheScore {
  id: string;
  name: string;
  category: string;
  overallScore: number;
  demandScore: number;
  competitionScore: number;
  rpmPotential: number;
  productionDifficulty: number;
  sponsorPotential: number;
  affiliatePotential: number;
  watchTimePotential: number;
  seasonality: "evergreen" | "seasonal" | "trend";
  trendDirection: "up" | "stable" | "down";
  estimatedMonthlyRpm: number;
  topCompetitors: string[];
  contentGaps: string[];
}

// ============================================================
// Video / Content Types
// ============================================================

export interface VideoProject {
  id: string;
  channelId: string;
  title: string;
  stage: PipelineStage;
  format: ContentFormat;
  niche: string;
  targetKeywords: string[];
  hookScore?: number;
  originalityScore?: number;
  thumbnailScore?: number;
  seoScore?: number;
  overallQualityScore?: number;
  complianceRisk?: RiskLevel;
  assignedAgents: string[];
  scriptId?: string;
  voiceTrackUrl?: string;
  thumbnailUrls?: string[];
  videoUrl?: string;
  publishedUrl?: string;
  scheduledFor?: string;
  publishedAt?: string;
  estimatedDurationSeconds?: number;
  actualDurationSeconds?: number;
  createdAt: string;
  updatedAt: string;
}

export interface Script {
  id: string;
  videoProjectId: string;
  title: string;
  hook: string;
  intro: string;
  problem: string;
  deepening: string;
  value: string;
  cta: string;
  fullText: string;
  wordCount: number;
  estimatedDurationSeconds: number;
  hookScore: number;
  retentionScore: number;
  naturalityScore: number;
  originalityScore: number;
  version: number;
  createdAt: string;
}

// ============================================================
// Agent Types
// ============================================================

export type AgentId =
  | "niche_hunter"
  | "opportunity_mapper"
  | "competitive_deconstruction"
  | "channel_architect"
  | "script_strategist"
  | "voice_persona"
  | "hook_specialist"
  | "retention_editor"
  | "thumbnail_psychology"
  | "title_architect"
  | "storyboard"
  | "format_localizer"
  | "asset_retrieval"
  | "video_assembly"
  | "audio_polish"
  | "caption"
  | "seo_intelligence"
  | "experimentation"
  | "watch_time_forensics"
  | "channel_portfolio"
  | "originality_transformation"
  | "rights_risk"
  | "monetization_readiness";

export interface Agent {
  id: AgentId;
  name: string;
  layer: 1 | 2 | 3 | 4 | 5;
  description: string;
  status: AgentStatus;
  lastRunAt?: string;
  tasksCompleted: number;
  successRate: number;
  avgDurationSeconds: number;
  tools: string[];
}

export interface AgentRun {
  id: string;
  agentId: AgentId;
  videoProjectId?: string;
  channelId?: string;
  status: AgentStatus;
  input: Record<string, unknown>;
  output?: Record<string, unknown>;
  errorMessage?: string;
  startedAt: string;
  completedAt?: string;
  durationSeconds?: number;
  tokensUsed?: number;
  cost?: number;
}

// ============================================================
// Quality Gate Types
// ============================================================

export interface QualityGate {
  stage: PipelineStage;
  checks: QualityCheck[];
  passed: boolean;
  passedAt?: string;
}

export interface QualityCheck {
  name: string;
  description: string;
  threshold: number;
  actualValue?: number;
  passed: boolean;
  required: boolean;
}

// ============================================================
// Experiment Types
// ============================================================

export interface Experiment {
  id: string;
  channelId: string;
  videoProjectId?: string;
  type: "thumbnail" | "title" | "hook" | "cta" | "upload_time" | "video_length";
  status: "planned" | "running" | "completed" | "cancelled";
  variants: ExperimentVariant[];
  winnerVariantId?: string;
  statisticalSignificance?: number;
  startedAt?: string;
  completedAt?: string;
  createdAt: string;
}

export interface ExperimentVariant {
  id: string;
  name: string;
  value: string;
  impressions: number;
  clicks: number;
  ctr: number;
  watchTimeMinutes: number;
}

// ============================================================
// Analytics Types
// ============================================================

export interface RetentionDataPoint {
  timestampSeconds: number;
  retentionPercent: number;
  isDropPoint: boolean;
  dropReason?: string;
}

export interface VideoAnalytics {
  videoId: string;
  views: number;
  watchTimeMinutes: number;
  avgViewDurationSeconds: number;
  avgRetentionPercent: number;
  ctr: number;
  likes: number;
  comments: number;
  shares: number;
  revenue: number;
  rpm: number;
  retentionCurve: RetentionDataPoint[];
  trafficSources: TrafficSource[];
  demographicsAge?: Record<string, number>;
  demographicsGender?: Record<string, number>;
  demographicsCountry?: Record<string, number>;
}

export interface TrafficSource {
  source: string;
  views: number;
  percentage: number;
  avgViewDuration: number;
}

// ============================================================
// Compliance Types
// ============================================================

export interface ComplianceReport {
  videoProjectId: string;
  originalityScore: number;
  similarityToOtherVideos: number;
  templateOveruseRisk: RiskLevel;
  copyrightRisk: RiskLevel;
  aiDisclosureRequired: boolean;
  aiDisclosureSet: boolean;
  sponsorDisclosureRequired: boolean;
  sponsorDisclosureSet: boolean;
  yppSafe: boolean;
  issues: ComplianceIssue[];
  recommendations: string[];
  checkedAt: string;
}

export interface ComplianceIssue {
  severity: RiskLevel;
  category: string;
  description: string;
  remediation: string;
}

// ============================================================
// SEO Types
// ============================================================

export interface SEOStrategy {
  videoProjectId: string;
  primaryKeyword: string;
  secondaryKeywords: string[];
  optimizedTitle: string;
  optimizedDescription: string;
  tags: string[];
  uploadTiming: string;
  targetTrafficSource: "search" | "suggested" | "home_feed" | "mixed";
  searchVolume: number;
  competitionLevel: "low" | "medium" | "high";
  recommendationFitScore: number;
  seoScore: number;
}

// ============================================================
// Monetization Types
// ============================================================

export interface MonetizationStatus {
  channelId: string;
  yppEligible: boolean;
  yppActive: boolean;
  subscribers: number;
  subscribersRequired: number;
  watchHours: number;
  watchHoursRequired: number;
  activeRevenueStreams: RevenueStream[];
  monthlyRevenue: number;
  projectedMonthlyRevenue: number;
  revenueByStream: Record<RevenueStream, number>;
  nextMilestones: Milestone[];
}

export interface Milestone {
  name: string;
  description: string;
  targetValue: number;
  currentValue: number;
  unit: string;
  estimatedDate?: string;
  completed: boolean;
}

// ============================================================
// API Response Types
// ============================================================

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface ApiError {
  detail: string;
  status: number;
  code?: string;
}
