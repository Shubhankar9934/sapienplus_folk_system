import { useQuery } from "@tanstack/react-query";
import type { DimCode } from "./dimensions";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

// ------------------------------------------------------------------ //
// Types
// ------------------------------------------------------------------ //
export interface Stats {
  countries: number;
  dimensions: number;
  frameworks: number;
  specialists: string[];
  research_grade: string | null;
  evidence_sources: number;
  reference_library_size: number;
  archetype_count: number;
  council_dashboard: Record<string, unknown>;
  research_quality: Record<string, unknown>;
  human_review_queue: number;
  run_metrics: Record<string, unknown> | null;
}

export interface CountryListItem {
  iso3: string;
  country: string;
  region: string | null;
  data_status: string | null;
  record_type: string | null;
  requires_human_review: boolean;
  scores: Record<DimCode, number | null>;
  confidence: Record<DimCode, string | null>;
  archetype: string | null;
  uniqueness: number | null;
  evidence_strength: number | null;
  council_agreement: number | null;
  consensus_verdict: string | null;
  research_grade: string | null;
}

export interface MapItem {
  iso3: string;
  country: string;
  region: string | null;
  scores: Record<DimCode, number | null>;
  confidence: Record<DimCode, string | null>;
}

export interface DimScore {
  dimension: DimCode;
  label: string;
  low_pole: string;
  high_pole: string;
  score: number | null;
  confidence: string | null;
  ci_low: number | null;
  ci_high: number | null;
  interpretation?: string | null;
}

export interface EvidenceStrength {
  overall: number | null;
  per_dimension: Record<string, number>;
}

export interface CouncilAgreement {
  overall: number | null;
  verdict: string | null;
  per_dimension: Record<
    string,
    {
      agreement: number;
      spread: number;
      specialists: {
        specialist: string;
        label: string;
        proposed_score: number;
        confidence: number;
      }[];
    }
  >;
}

export interface RegionalContext {
  region: string;
  per_dimension: Record<
    string,
    { score: number; region_average: number; delta: number }
  >;
}

export interface GlobalDistribution {
  per_dimension: Record<
    string,
    { score: number; percentile: number; rank: number; total: number }
  >;
}

export interface TrustBreakdown {
  frameworks: string[];
  framework_count: number;
  specialist_count: number;
  specialists: string[];
  evidence_reviewed: boolean;
  calibration_passed: boolean | null;
  human_reviewed: boolean;
  provider_diversity: number | null;
}

// ---- Culture-first content types ----
export interface DimensionSnapshot {
  dimension: DimCode;
  score: number;
  reading: string;
  /** One-sentence grounded cultural explanation (falls back to reading). */
  explanation: string;
}

export interface Observation {
  text: string;
  claim_ids: string[];
  sources_count: number;
}

export interface ThemeConfidence {
  evidence_strength: number;
  expert_agreement: number;
  framework_agreement: number;
  evidence_strength_label: string;
  expert_agreement_label: string;
  framework_agreement_label: string;
  /** Deterministic one-sentence "why this confidence" narrative. */
  confidence_explanation: string;
}

export interface UniquenessFacet {
  title: string;
  explanation: string;
  claim_ids: string[];
  sources_count: number;
}

export interface ExperienceVariation {
  group_a: string;
  group_b: string;
  difference: string;
  claim_ids: string[];
  sources_count: number;
}

export interface CulturalTheme {
  title: string;
  confidence: ThemeConfidence;
  sources_count: number;
  observations: Observation[];
  historical_roots: Observation[];
}

export interface CompetingForce {
  pulls_toward: string;
  but_also: string;
  explanation: string;
  claim_ids: string[];
  sources_count: number;
}

export interface LivedExperience {
  daily_life: Observation[];
  workplace_norms: Observation[];
  communication_style: Observation[];
  friendship_social: Observation[];
  society: Observation[];
  social_mistakes_to_avoid: Observation[];
  status_signals: Observation[];
}

export interface Archetype {
  title: string;
  summary: string;
  claim_ids: string[];
  sources_count: number;
}

export interface CommunicationSignal {
  phrase: string;
  meaning: string;
  claim_ids: string[];
  sources_count: number;
}

export interface TransitionAxis {
  axis: string;
  older: string;
  younger: string;
  claim_ids: string[];
  sources_count: number;
}

export interface FriendshipFacet {
  label: string;
  detail: string;
  claim_ids: string[];
  sources_count: number;
}

export interface FriendshipMap {
  making_friends: FriendshipFacet;
  friendship_depth: FriendshipFacet;
  circle_size: FriendshipFacet;
  trust_formation: FriendshipFacet;
  work_personal_mixing: FriendshipFacet;
}

export interface SimilarCulture {
  iso3: string;
  country: string;
  similarity: number;
  explanation: string;
  claim_ids: string[];
  sources_count: number;
}

export interface RelativeInsight {
  text: string;
  dimension: DimCode | null;
  neighbour_iso3: string;
  delta: number;
}

export interface CouncilView {
  specialist: string;
  reasoning: string;
  suggested_score: number;
}

export interface CountryProfile {
  iso3: string;
  country: string;
  region: string | null;
  data_status: string | null;
  record_type: string | null;
  requires_human_review: boolean;
  processing_date: string | null;
  // Culture-first content
  snapshot: DimensionSnapshot[];
  executive_summary: string | null;
  cultural_archetype: Archetype | null;
  good_for: string[];
  /** @deprecated alias of good_for kept for older builds */
  best_for: string[];
  /** Deterministic executive snapshot: 4-6 one-sentence bullets. */
  culture_at_a_glance: string[];
  cultural_themes: CulturalTheme[];
  historical_drivers: Observation[];
  competing_forces: CompetingForce[];
  lived_experience: LivedExperience;
  /** Grounded "what life feels like" narrative block (may be empty). */
  life_feels_like: Observation | null;
  newcomer_first_impressions: Observation[];
  success_factors: Observation[];
  failure_factors: Observation[];
  friendship_map: FriendshipMap | null;
  communication_decoder: CommunicationSignal[];
  culture_in_transition: TransitionAxis[];
  /** How different co-existing groups experience the country. */
  experience_variations: ExperienceVariation[];
  similar_cultures: SimilarCulture[];
  /** Grounded "what makes this country unique vs neighbours" facets. */
  country_uniqueness: UniquenessFacet[];
  regional_distinctiveness: RelativeInsight[];
  council_views: Record<string, CouncilView[]>;
  // Visible Cultural Fingerprint (scores) + methodology
  scores: Record<DimCode, DimScore>;
  neighbours: Neighbour[];
  anchor_positions: AnchorPosition[];
  archetype: string | null;
  uniqueness: number | null;
  evidence_strength: EvidenceStrength;
  council_agreement: CouncilAgreement;
  regional_context: RegionalContext;
  global_distribution: GlobalDistribution;
  research_grade: string | null;
  trust: TrustBreakdown;
}

export interface Neighbour {
  iso3: string;
  country: string;
  d1: number;
  d2: number;
  d3: number;
  d4: number;
  relation: string;
}

export interface AnchorPosition {
  dimension: string;
  anchor_iso3: string;
  direction: string;
  magnitude: number;
  reason: string;
}

export interface KeySource {
  claim_id: string;
  source_id: string;
  title: string;
  url: string;
  author: string;
  publication_year: number | null;
  excerpt: string;
  dimension: string;
  support_direction: string;
}

export interface DimensionDetail {
  iso3: string;
  dimension: DimCode;
  label: string;
  low_pole: string;
  high_pole: string;
  score: number | null;
  confidence: string | null;
  council_views: CouncilView[];
  summary: string | null;
  final_rationale: string | null;
  adjustment_type: string | null;
  evidence_strength: number | null;
  confidence_breakdown: {
    coverage?: number;
    agreement?: number;
    evidence?: number;
    stability?: number;
    final?: number;
  };
  council_impact: {
    baseline?: number | null;
    final?: number | null;
    change?: number | null;
    adjustment_type?: string | null;
    reason?: string | null;
  };
}

export interface SourceEntry {
  claim_id: string;
  source_id: string;
  title: string;
  url: string | null;
  author: string | null;
  publication_year: number | null;
  excerpt: string;
}

export interface SimilarCountry {
  iso3: string;
  country: string;
  similarity: number;
  distance: number;
}

export interface SimilarResponse {
  iso3: string;
  ready: boolean;
  note?: string;
  most_similar: SimilarCountry[];
  most_different: SimilarCountry[];
}

export interface SpecialistPosition {
  iso3: string;
  specialist: string;
  dimension: string;
  proposed_score: number;
  strongest_supporting: string;
  strongest_opposing: string;
  biggest_weakness: string;
  alternative_score: number;
  confidence: number;
}

export interface Challenge {
  iso3: string;
  challenger: string;
  target: string;
  dimension: string;
  attack_type: string;
  critique: string;
  target_response: string;
  accepted: boolean;
  impact: number;
}

export interface CouncilResponse {
  iso3: string;
  country: string;
  agreement: CouncilAgreement;
  council_views: Record<string, CouncilView[]>;
  positions: SpecialistPosition[];
  influence_records: {
    dimension: string;
    baseline_score: number;
    specialist_recommendation: number;
    specialist_confidence: number;
    evidence_strength: number;
    evidence_quality: number;
    disagreement_index: number;
    specialist_influence_weight: number;
    rationale: string;
  }[];
  challenges: Challenge[];
  diversity_v2: unknown;
}

export interface SourcesResponse {
  iso3: string;
  total_sources: number;
  verified: number;
  verified_pct: number;
  average_quality: number | null;
  by_type: { type: string; count: number }[];
  sources: SourceEntry[];
  references: {
    citation: string;
    source_type: string;
    data_point: string;
    url_or_doi: string | null;
    folk_dimension: string;
    direction: string;
    verified: boolean;
    ref_id: string;
  }[];
}

export interface ArchetypeCluster {
  label: string;
  centroid: Record<DimCode, number>;
  size: number;
  members: { iso3: string; country: string }[];
}

export interface RankingRow {
  iso3: string;
  country: string;
  region: string | null;
  score: number;
}

export interface RankingResponse {
  dimension: DimCode;
  label: string;
  highest: RankingRow[];
  lowest: RankingRow[];
}

export interface RegionRankingResponse {
  dimension: DimCode;
  label: string;
  regions: { region: string; average: number }[];
}

export interface CompareResponse {
  countries: {
    iso3: string;
    country: string;
    region: string | null;
    scores: Record<DimCode, number>;
    confidence: Record<DimCode, string | null>;
    archetype: string | null;
  }[];
}

// ------------------------------------------------------------------ //
// Hooks
// ------------------------------------------------------------------ //
export const useStats = () =>
  useQuery({ queryKey: ["stats"], queryFn: () => get<Stats>("/api/stats") });

export const useCountries = () =>
  useQuery({
    queryKey: ["countries"],
    queryFn: () => get<CountryListItem[]>("/api/countries"),
  });

export const useMap = () =>
  useQuery({ queryKey: ["map"], queryFn: () => get<MapItem[]>("/api/map") });

export const useCountry = (iso3: string) =>
  useQuery({
    queryKey: ["country", iso3],
    queryFn: () => get<CountryProfile>(`/api/countries/${iso3}`),
    enabled: !!iso3,
  });

export const useDimension = (iso3: string, dim: string) =>
  useQuery({
    queryKey: ["dimension", iso3, dim],
    queryFn: () =>
      get<DimensionDetail>(`/api/countries/${iso3}/dimensions/${dim}`),
    enabled: !!iso3 && !!dim,
  });

export const useSimilar = (iso3: string) =>
  useQuery({
    queryKey: ["similar", iso3],
    queryFn: () => get<SimilarResponse>(`/api/countries/${iso3}/similar`),
    enabled: !!iso3,
  });

export const useCouncil = (iso3: string) =>
  useQuery({
    queryKey: ["council", iso3],
    queryFn: () => get<CouncilResponse>(`/api/countries/${iso3}/council`),
    enabled: !!iso3,
  });

export const useSources = (iso3: string) =>
  useQuery({
    queryKey: ["sources", iso3],
    queryFn: () => get<SourcesResponse>(`/api/countries/${iso3}/sources`),
    enabled: !!iso3,
  });

export const useArchetypes = () =>
  useQuery({
    queryKey: ["archetypes"],
    queryFn: () =>
      get<{ clusters: ArchetypeCluster[]; ready: boolean; note: string | null }>(
        "/api/archetypes"
      ),
  });

export const useRankings = (dim: string) =>
  useQuery({
    queryKey: ["rankings", dim],
    queryFn: () => get<RankingResponse>(`/api/rankings?dim=${dim}`),
  });

export const useRegionRankings = (dim: string) =>
  useQuery({
    queryKey: ["region-rankings", dim],
    queryFn: () =>
      get<RegionRankingResponse>(`/api/rankings?dim=${dim}&scope=region`),
  });

export const useCompare = (isos: string[]) =>
  useQuery({
    queryKey: ["compare", isos.join(",")],
    queryFn: () => get<CompareResponse>(`/api/compare?isos=${isos.join(",")}`),
    enabled: isos.length > 0,
  });
