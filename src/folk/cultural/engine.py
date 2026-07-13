"""Cultural Themes engine (the one grounded LLM stage of the culture-first profile).

The model is given the evidence claims the specialists already discovered and
asked ONLY to cluster + rephrase them into self-named cultural themes with short,
source-linked observations, plus grounded historical drivers, a punchy executive
summary, competing forces, a country-specific ``good_for``, and a grounded
lived-experience layer (workplace/communication/friendship/mistakes/status). It
cannot mint new cultural facts.

A deterministic grounding filter then drops any item whose ``claim_ids`` do not
resolve to a real claim, drops emptied themes, and computes each item's
``sources_count`` and each theme's ``confidence`` (evidence strength). The
snapshot (Cultural Fingerprint), council views, and regional distinctiveness are
assembled deterministically by :mod:`folk.cultural.assembly`.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from folk.cultural.assembly import (
    build_council_views,
    build_regional_distinctiveness,
    build_similar_cultures,
    build_snapshot,
    build_uniqueness_seed,
    expert_agreement,
    framework_agreement,
    theme_confidence,
)
from folk.llm.factory import ProviderFactory
from folk.llm.prompts import PromptLibrary, get_prompt_library
from folk.models.cultural import (
    LIFE_DOMAIN_TO_FIELD,
    Archetype,
    CommunicationSignal,
    CompetingForce,
    CulturalProfile,
    CulturalTheme,
    CulturalThemesDraft,
    DimensionSnapshot,
    DimensionTake,
    ExperienceVariation,
    FriendshipFacet,
    FriendshipMap,
    HistoricalDriver,
    LivedExperience,
    Observation,
    SimilarCulture,
    ThemeConfidence,
    TransitionAxis,
    UniquenessFacet,
)
from folk.models.enums import DIMENSIONS, Dimension
from folk.models.knowledge import CountryKnowledgePack
from folk.models.metrics import CallMetric
from folk.models.research import SpecialistAssessment, SpecialistEvidencePack

# Bound the executive summary so it can never become an essay.
EXEC_SUMMARY_MAX_CHARS = 700
MAX_THEMES = 6
MAX_CLAIMS_TO_MODEL = 80
MAX_GOOD_FOR = 4
MAX_LIVED_PER_DOMAIN = 5
MAX_PRACTICAL = 8          # newcomer / success / failure lists (spec: 4-8)
MAX_COMM_SIGNALS = 8       # communication decoder entries
MAX_TRANSITION = 4         # culture-in-transition axes
MAX_CONTRADICTIONS = 4     # cultural contradictions
MAX_EXPERIENCE_VARIATIONS = 4   # how-different-groups contrasts
MAX_UNIQUENESS = 4         # country-uniqueness facets
MAX_GLANCE = 6             # culture-at-a-glance bullets (spec: 4-6)
MIN_GLANCE = 4

# life_domain tags that feed dedicated top-level sections (not LivedExperience).
_SUCCESS_DOMAIN = "success_factor"
_FAILURE_DOMAIN = "failure_factor"
_COMM_DECODER_DOMAIN = "communication_decoder"
_TRANSITION_DOMAIN = "cultural_transition"

# Dimension restatements / near-synonyms that may NOT stand alone as a theme
# name (the theme-validation banlist). A theme is dropped only when ALL its
# significant tokens are banned (so "Reserved Trust" / "Nunchi and Social
# Awareness" survive, but "Achievement Culture" / "Collective Commitment" do not).
_DIMENSION_BANLIST: frozenset[str] = frozenset({
    "achievement", "achiever", "achieving", "drive", "driven", "driving",
    "collectivism", "collective", "collectivist", "collectivity",
    "individualism", "individual", "individualist", "individualistic",
    "identity", "hierarchy", "hierarchical", "structure", "structured",
    "structural",     "certainty", "certain", "expression", "expressive",
    "emotional", "emotion", "emotions",
    "openness", "open", "restraint", "restrained", "reserved",
    "community", "communal", "independence", "independent",
    "commitment", "orientation", "culture", "society", "societal",
})
# Filler tokens ignored when judging whether a title is a pure restatement.
_BANLIST_FILLER: frozenset[str] = frozenset({
    "and", "the", "of", "a", "an", "&", "to", "in", "with", "for",
})


@dataclass
class _ClaimRef:
    source_id: str
    seat: str


class CulturalProfileEngine:
    def __init__(self, factory: ProviderFactory | None = None,
                 prompts: PromptLibrary | None = None) -> None:
        self.factory = factory or ProviderFactory()
        self.prompts = prompts or get_prompt_library()
        self.provider = self.factory.get("cultural")
        # Per-call lookups (claim_id -> text / dimension / life-domain),
        # populated in generate().
        self._claim_text: dict[str, str] = {}
        self._claim_dim: dict[str, Dimension] = {}
        self._claim_life: dict[str, str] = {}

    # ------------------------------------------------------------------ #
    def generate(
        self,
        pack: CountryKnowledgePack,
        final_scores: dict[Dimension, int],
        packs: list[SpecialistEvidencePack],
        assessments: list[SpecialistAssessment],
    ) -> tuple[CulturalProfile, CallMetric]:
        claim_index = self._build_claim_index(packs)
        self._claim_text = {c.claim_id: (c.claim or "")
                            for p in packs for c in p.claims if c.claim_id}
        self._claim_dim = {c.claim_id: c.supporting_dimension
                           for p in packs for c in p.claims
                           if c.claim_id and c.supporting_dimension is not None}
        self._claim_life = {c.claim_id: c.life_domain
                            for p in packs for c in p.claims
                            if c.claim_id and c.life_domain}

        # Deterministic pieces (no LLM, no invention).
        snapshot = build_snapshot(final_scores)
        council_views = build_council_views(assessments)
        regional = build_regional_distinctiveness(pack, final_scores)
        similar_seed = build_similar_cultures(pack, final_scores)
        uniqueness_seed = build_uniqueness_seed(pack, final_scores)

        # The one grounded LLM call (mock path uses _compose()).
        hint = self._compose(pack, snapshot, claim_index, similar_seed)
        system = self.prompts.preamble()
        user = self._user_prompt(pack, claim_index, similar_seed, uniqueness_seed)
        draft, metric = self.provider.generate_structured(
            CulturalThemesDraft, system, user,
            mock_hint=hint.model_dump(mode="json"),
            temperature=0.4, role="cultural", iso3=pack.iso3, phase="cultural",
        )

        # Deterministic grounding filter + provenance/confidence.
        themes = self._filter_themes(draft.cultural_themes, claim_index, assessments, pack)
        drivers = self._filter_grounded(draft.historical_drivers, claim_index)
        forces = self._filter_contradictions(draft.competing_forces, claim_index)
        good_for = self._clean_good_for(draft.good_for)
        summary = (draft.executive_summary or "").strip()[:EXEC_SUMMARY_MAX_CHARS]
        lived = self._filter_lived(draft.lived_experience, claim_index)
        life_feels = self._filter_life_feels_like(draft.life_feels_like, claim_index)
        archetype = self._filter_archetype(draft.cultural_archetype, claim_index)
        newcomers = self._prefer_multi_source(
            self._filter_grounded(draft.newcomer_first_impressions, claim_index))[:MAX_PRACTICAL]
        success = self._prefer_multi_source(
            self._filter_grounded(draft.success_factors, claim_index))[:MAX_PRACTICAL]
        failure = self._prefer_multi_source(
            self._filter_grounded(draft.failure_factors, claim_index))[:MAX_PRACTICAL]
        decoder = self._filter_decoder(draft.communication_decoder, claim_index)
        transition = self._filter_transition(draft.culture_in_transition, claim_index)
        variations = self._filter_variations(draft.experience_variations, claim_index)
        friendship = self._filter_friendship(draft.friendship_map, claim_index)
        similar = self._merge_similar(similar_seed, draft.similar_cultures, claim_index)
        uniqueness = self._filter_uniqueness(draft.country_uniqueness, claim_index)
        # Per-dimension one-sentence explanations (grounded; reading fallback).
        snapshot = self._merge_dimension_takes(snapshot, draft.dimension_takes, claim_index)
        # Deterministic executive snapshot from the strongest clustered material.
        glance = self._build_glance(themes, lived, newcomers, success, failure)

        profile = CulturalProfile(
            iso3=pack.iso3, country=pack.country, region=pack.region,
            snapshot=snapshot, executive_summary=summary,
            cultural_archetype=archetype, good_for=good_for,
            culture_at_a_glance=glance,
            cultural_themes=themes, historical_drivers=drivers,
            competing_forces=forces, lived_experience=lived,
            life_feels_like=life_feels,
            newcomer_first_impressions=newcomers, success_factors=success,
            failure_factors=failure, friendship_map=friendship,
            communication_decoder=decoder, culture_in_transition=transition,
            experience_variations=variations,
            similar_cultures=similar, country_uniqueness=uniqueness,
            regional_distinctiveness=regional, council_views=council_views,
        )
        return profile, metric

    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_claim_index(packs: list[SpecialistEvidencePack]) -> dict[str, _ClaimRef]:
        index: dict[str, _ClaimRef] = {}
        for p in packs:
            seat = p.seat.value if hasattr(p.seat, "value") else str(p.seat)
            for c in p.claims:
                if c.claim_id:
                    index[c.claim_id] = _ClaimRef(source_id=c.source_id, seat=seat)
        return index

    def _user_prompt(self, pack: CountryKnowledgePack,
                     claim_index: dict[str, _ClaimRef],
                     similar_seed: list[SimilarCulture],
                     uniqueness_seed: list[str] | None = None) -> str:
        lines = [self.prompts.cultural_themes_prompt(),
                 f"\nCOUNTRY: {pack.country} ({pack.iso3})"]
        if similar_seed:
            seeds = ", ".join(f"{s.country} ({s.iso3})" for s in similar_seed)
            lines.append(
                "\nCULTURALLY CLOSEST COUNTRIES (fixed set - write a grounded "
                f"`similar_cultures` explanation for THESE only, do not add others): {seeds}")
        if uniqueness_seed:
            lines.append(
                "\nNEAREST NEIGHBOURS TO DIFFERENTIATE AGAINST (write "
                "`country_uniqueness` facets that explain why "
                f"{pack.country} is distinct from THESE): {', '.join(uniqueness_seed)}")
        lines.append(
            "\nEVIDENCE CLAIMS (cluster ONLY these; cite claim_ids). Claims tagged "
            "[life:<domain>] are lived-experience evidence for that domain:")
        # Pull claim texts back out of the packs for the prompt body.
        # (claim_index only stores provenance; we re-read the text here.)
        seen = 0
        for cid, _ref in claim_index.items():
            text = self._claim_text.get(cid, "")
            if not text:
                continue
            domain = self._claim_life.get(cid)
            tag = f" [life:{domain}]" if domain else ""
            lines.append(f"- {cid}{tag}: {text}")
            seen += 1
            if seen >= MAX_CLAIMS_TO_MODEL:
                break
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Deterministic, evidence-derived theme titles for the offline/mock path,
    # keyed by the snapshot pole each dimension leans toward. These are concrete,
    # memorable culture names that are NOT dimension restatements (they survive
    # the _is_dimension_restatement validator), so the mock path never models
    # dimension-shaped themes.
    _OFFLINE_THEME_TITLE: dict[tuple[str, bool], str] = {
        ("D1", True): "Standing on Your Own", ("D1", False): "Belonging First",
        ("D2", True): "Saying It Plainly", ("D2", False): "Reading the Room",
        ("D3", True): "A Place for Everything", ("D3", False): "Rolling With It",
        ("D4", True): "Earning Your Place", ("D4", False): "Enough Is Enough",
    }

    def _compose(self, pack: CountryKnowledgePack, snapshot,
                 claim_index: dict[str, _ClaimRef],
                 similar_seed: list[SimilarCulture]) -> CulturalThemesDraft:
        """Deterministic offline draft: group claims into evidence-derived themes,
        a lived-experience layer, and the practical human-experience sections so
        the mock path produces grounded, schema-valid, non-template output."""
        lean_high = {s.dimension.value: s.score >= 50 for s in snapshot}

        # Cluster non-lived claims by dimension into concretely-named themes.
        by_dim: dict[Dimension, list[str]] = {d: [] for d in DIMENSIONS}
        for cid in claim_index:
            if self._claim_life.get(cid):
                continue  # lived-experience claims feed the lived layer
            dim = self._claim_dim.get(cid)
            by_dim[dim if dim is not None else Dimension.D1].append(cid)

        themes: list[CulturalTheme] = []
        for d in DIMENSIONS:
            cids = by_dim[d]
            if not cids:
                continue
            # Cluster 2-3 related claims per observation (Pattern -> Explanation
            # -> Consequence) so offline observations are genuinely multi-source.
            obs = self._cluster_pec(cids)[:4]
            title = self._OFFLINE_THEME_TITLE.get((d.value, lean_high.get(d.value, True)),
                                                  d.label)
            themes.append(CulturalTheme(title=title, observations=obs))

        # Bucket life_domain-tagged claims: some feed LivedExperience, some feed
        # the dedicated practical sections.
        lived_payload: dict[str, list[str]] = {}
        success_cids: list[str] = []
        failure_cids: list[str] = []
        decoder_cids: list[str] = []
        transition_cids: list[str] = []
        for cid, domain in self._claim_life.items():
            if domain == _SUCCESS_DOMAIN:
                success_cids.append(cid)
            elif domain == _FAILURE_DOMAIN:
                failure_cids.append(cid)
            elif domain == _COMM_DECODER_DOMAIN:
                decoder_cids.append(cid)
            elif domain == _TRANSITION_DOMAIN:
                transition_cids.append(cid)
            else:
                field = LIFE_DOMAIN_TO_FIELD.get(domain)
                if field:
                    lived_payload.setdefault(field, []).append(cid)
        lived = LivedExperience(**{f: self._merge_by_text(cids)
                                   for f, cids in lived_payload.items()})

        drivers = [HistoricalDriver(text=self._claim_text.get(c, c)[:200], claim_ids=[c])
                   for c in list(claim_index)[:3] if not self._claim_life.get(c)]
        readings = ", ".join(s.reading.lower() for s in snapshot)
        summary = (f"{pack.country} reads as {readings}. Newcomers feel these patterns most "
                   f"in how work, friendships, and disagreement actually play out day to day.")

        # Archetype: a concrete identity from the leading two dimension poles.
        arche_cids = [c for c in by_dim.get(Dimension.D1, [])][:2]
        archetype = Archetype(
            title=self._offline_archetype(pack, lean_high),
            summary=f"How {pack.country} tends to operate, in two words.",
            claim_ids=arche_cids,
        )

        # Newcomers notice first = the first lived observation per domain.
        newcomers = [obs[0] for obs in
                     (self._merge_by_text(cids) for cids in lived_payload.values()) if obs]

        decoder = [CommunicationSignal(
            phrase=self._claim_text.get(c, c)[:80], meaning=self._claim_text.get(c, c)[:160],
            claim_ids=[c]) for c in decoder_cids[:MAX_COMM_SIGNALS]]
        transition = [TransitionAxis(
            axis="Generational", older="More traditional", younger="More individualistic",
            claim_ids=[c]) for c in transition_cids[:MAX_TRANSITION]]

        # How different groups experience the country (co-existing contrasts).
        variations: list[ExperienceVariation] = []
        if transition_cids:
            variations.append(ExperienceVariation(
                group_a="Younger, urban residents", group_b="Older, rural communities",
                difference=("Norms differ across generations and places, which is why "
                            "younger urban residents tend to act more individualistically. "
                            "This means newcomers meet very different expectations "
                            "depending on who they are with."),
                claim_ids=list(transition_cids[:MAX_EXPERIENCE_VARIATIONS])))

        # "What life feels like": a grounded narrative synthesized from several
        # distinct lived-experience domains (so it is genuinely multi-source).
        life_feels_like = self._offline_life_feels_like(pack, lived_payload)

        # Country uniqueness: differentiate against the nearest neighbours.
        uniq_ids = arche_cids or list(claim_index)[:2]
        country_uniqueness = [UniquenessFacet(
            title=f"Distinct from {s.country}",
            explanation=(f"{pack.country} shares a region with {s.country} but its "
                         "everyday balance of the patterns above plays out differently, "
                         "which is why the two feel distinct to a newcomer."),
            claim_ids=list(uniq_ids))
            for s in similar_seed[:2]] if uniq_ids else []

        # Per-dimension one-sentence cultural explanations.
        dimension_takes = [DimensionTake(
            dimension=d, explanation=self._first_sentence(
                self._claim_text.get(by_dim[d][0], "")) or "",
            claim_ids=by_dim[d][:2])
            for d in DIMENSIONS if by_dim.get(d)]

        return CulturalThemesDraft(
            executive_summary=summary,
            cultural_archetype=archetype,
            good_for=self._offline_good_for(pack, snapshot),
            cultural_themes=themes,
            historical_drivers=drivers,
            competing_forces=[CompetingForce(
                pulls_toward=self._OFFLINE_THEME_TITLE[("D1", lean_high.get("D1", True))],
                but_also=self._OFFLINE_THEME_TITLE[("D1", not lean_high.get("D1", True))],
                explanation=f"{pack.country} holds both of these in tension at once.",
                claim_ids=arche_cids or list(claim_index)[:1])],
            lived_experience=lived,
            life_feels_like=life_feels_like,
            newcomer_first_impressions=newcomers[:MAX_PRACTICAL],
            success_factors=self._cluster_pec(success_cids)[:MAX_PRACTICAL],
            failure_factors=self._cluster_pec(failure_cids)[:MAX_PRACTICAL],
            friendship_map=self._offline_friendship(lived_payload, lean_high),
            communication_decoder=decoder,
            culture_in_transition=transition,
            experience_variations=variations,
            similar_cultures=[SimilarCulture(
                iso3=s.iso3, country=s.country, similarity=s.similarity,
                explanation=f"{pack.country} and {s.country} share several of the same "
                            "everyday patterns.",
                claim_ids=list(claim_index)[:1]) for s in similar_seed],
            country_uniqueness=country_uniqueness,
            dimension_takes=dimension_takes,
        )

    def _offline_life_feels_like(self, pack: CountryKnowledgePack,
                                 lived_payload: dict[str, list[str]]) -> Observation:
        """Synthesize a short grounded life-feels-like narrative from the first
        claim of several distinct lived-experience domains (multi-source)."""
        order = ["daily_life", "workplace_norms", "friendship_social",
                 "communication_style", "status_signals"]
        picks: list[str] = []
        claim_ids: list[str] = []
        for field in order:
            cids = lived_payload.get(field)
            if not cids:
                continue
            sentence = self._first_sentence(self._claim_text.get(cids[0], ""))
            if sentence:
                picks.append(sentence.rstrip("."))
                claim_ids.append(cids[0])
            if len(picks) >= 3:
                break
        if not picks:
            return Observation()
        text = (f"Day to day, life in {pack.country} is shaped by how "
                + "; ".join(self._lower_first(p) for p in picks)
                + ". Together these patterns set the rhythm a newcomer adjusts to first.")
        return Observation(text=text, claim_ids=claim_ids)

    def _cluster_pec(self, cids: list[str]) -> list[Observation]:
        """Cluster claims into Pattern -> Explanation -> Consequence observations.

        Identical-text claims are merged first (so corroboration shows as real
        source density), then up to three base observations are synthesized into
        one multi-clause insight whose claim_ids span all of them."""
        base = self._merge_by_text(cids)
        out: list[Observation] = []
        for i in range(0, len(base), 3):
            out.append(self._pec_from(base[i:i + 3]))
        return out

    def _pec_from(self, chunk: list[Observation]) -> Observation:
        """Synthesize one Pattern -> Explanation -> Consequence observation."""
        ids: list[str] = []
        for o in chunk:
            for c in o.claim_ids:
                if c not in ids:
                    ids.append(c)
        texts = [self._first_sentence(o.text) for o in chunk if o.text]
        texts = [t for t in texts if t]
        if not texts:
            return Observation(text="", claim_ids=ids)
        parts = [texts[0].rstrip(".")]
        if len(texts) >= 2:
            parts.append(f", which is why {self._lower_first(texts[1]).rstrip('.')}")
        if len(texts) >= 3:
            parts.append(f". This means {self._lower_first(texts[2])}")
        text = "".join(parts)
        if not text.endswith((".", "!", "?")):
            text += "."
        return Observation(text=text, claim_ids=ids)

    @staticmethod
    def _lower_first(text: str) -> str:
        t = (text or "").strip()
        return (t[0].lower() + t[1:]) if t else t

    @staticmethod
    def _offline_archetype(pack: CountryKnowledgePack, lean_high: dict[str, bool]) -> str:
        """A concrete two-word identity for the offline/mock path."""
        first = "Independent" if lean_high.get("D1", True) else "Communal"
        second = ("Builder" if lean_high.get("D3", True) else "Improviser")
        if lean_high.get("D4", True):
            second = "Achiever"
        return f"The {first} {second}"

    def _offline_friendship(self, lived_payload: dict[str, list[str]],
                            lean_high: dict[str, bool]) -> FriendshipMap:
        """Build the offline friendship map from any friendship_social claims."""
        cids = lived_payload.get("friendship_social", [])
        if not cids:
            return FriendshipMap()
        slow = not lean_high.get("D2", True)  # restrained -> slower to open up
        cid = [cids[0]]
        return FriendshipMap(
            making_friends=FriendshipFacet(label="Slow" if slow else "Open", claim_ids=cid),
            friendship_depth=FriendshipFacet(label="High" if slow else "Moderate", claim_ids=cid),
            circle_size=FriendshipFacet(label="Small" if slow else "Broad", claim_ids=cid),
            trust_formation=FriendshipFacet(label="Slow" if slow else "Quick", claim_ids=cid),
            work_personal_mixing=FriendshipFacet(
                label="Limited" if slow else "Fluid", claim_ids=cid),
        )

    def _merge_by_text(self, cids: list[str]) -> list[Observation]:
        """Group claims with identical text into one observation that carries all
        of their claim_ids (so corroborated findings show real source density)."""
        by_text: dict[str, list[str]] = {}
        order: list[str] = []
        for c in cids:
            text = self._claim_text.get(c, c)[:200]
            if text not in by_text:
                order.append(text)
            by_text.setdefault(text, []).append(c)
        return [Observation(text=text, claim_ids=by_text[text]) for text in order]

    @staticmethod
    def _offline_good_for(pack: CountryKnowledgePack, snapshot) -> list[str]:
        """A small, country-flavoured good_for for the offline/mock path."""
        lean = {s.dimension.value: s.score for s in snapshot}
        out: list[str] = []
        if lean.get("D4", 50) >= 58:
            out.append("Career-driven professionals")
        if lean.get("D3", 50) >= 58:
            out.append("Long-term planning and operations")
        if lean.get("D1", 50) < 50:
            out.append("Relationship-led business")
        if lean.get("D2", 50) >= 58:
            out.append("Open, expressive teams")
        if not out:
            out.append(f"Understanding {pack.country}'s everyday culture")
        return out[:MAX_GOOD_FOR]

    # ------------------------------------------------------------------ #
    def _filter_themes(self, themes: list[CulturalTheme],
                       claim_index: dict[str, _ClaimRef],
                       assessments: list[SpecialistAssessment],
                       pack: CountryKnowledgePack) -> list[CulturalTheme]:
        out: list[CulturalTheme] = []
        for theme in themes[:MAX_THEMES * 2]:
            # Theme-name validation: drop pure dimension restatements.
            if self._is_dimension_restatement(theme.title):
                continue
            observations = self._prefer_multi_source(
                self._filter_grounded(theme.observations, claim_index))
            roots = self._filter_grounded(theme.historical_roots, claim_index)
            if not observations:
                continue  # drop empty themes
            theme.observations = observations
            theme.historical_roots = roots
            # Theme confidence from distinct claims/sources/specialists across all items.
            claim_ids, source_ids, seats = set(), set(), set()
            for item in observations + roots:
                for cid in item.claim_ids:
                    ref = claim_index.get(cid)
                    if not ref:
                        continue
                    claim_ids.add(cid)
                    if ref.source_id:
                        source_ids.add(ref.source_id)
                    if ref.seat:
                        seats.add(ref.seat)
            theme.sources_count = len(source_ids)
            modal_dim = self._modal_dimension(claim_ids)
            evidence = theme_confidence(len(claim_ids), len(source_ids), len(seats))
            expert = expert_agreement(assessments, modal_dim)
            framework = framework_agreement(pack, modal_dim)
            theme.confidence = ThemeConfidence(
                evidence_strength=evidence,
                expert_agreement=expert,
                framework_agreement=framework,
                confidence_explanation=self._confidence_explanation(
                    evidence, expert, framework, claim_ids),
            )
            out.append(theme)
        out.sort(key=lambda t: t.confidence.evidence_strength, reverse=True)
        return out[:MAX_THEMES]

    # ------------------------------------------------------------------ #
    @staticmethod
    def _is_dimension_restatement(title: str) -> bool:
        """True when a theme name is just a dimension restatement / synonym.

        A title is rejected only when EVERY significant token (after dropping
        filler words) is in the banlist - so "Achievement Culture" and
        "Collective Commitment" are dropped, while "Reserved Trust" and "Nunchi
        and Social Awareness" survive (they carry a non-banned token)."""
        tokens = [t for t in re.split(r"[^a-z]+", (title or "").lower()) if t]
        significant = [t for t in tokens if t not in _BANLIST_FILLER]
        if not significant:
            return True  # empty/filler-only title is useless
        return all(t in _DIMENSION_BANLIST for t in significant)

    def _confidence_explanation(self, evidence: int, expert: int, framework: int,
                                claim_ids) -> str:
        """One deterministic sentence explaining the theme's confidence.

        Built from which of the three components is strongest/weakest plus the
        theme's dominant evidence composition (modal life-domain), so users
        understand *why* a confidence reads moderate."""
        def band(v: int) -> str:
            if v >= 70:
                return "strong"
            if v >= 50:
                return "moderate"
            return "limited"

        parts: list[str] = []
        if expert >= 70:
            parts.append("Experts broadly agree on this pattern")
        elif expert >= 50:
            parts.append("Experts mostly agree on this pattern")
        else:
            parts.append("Experts are divided on this pattern")

        if framework >= 70:
            parts.append("and the cross-framework signal is consistent")
        elif framework >= 50:
            parts.append("and the cross-framework signal is broadly consistent")
        else:
            parts.append("and the cross-framework signal is mixed")

        domain = self._modal_life_domain(claim_ids)
        ev_band = band(evidence)
        if domain:
            tail = (f", but the evidence is {ev_band} and concentrated in "
                    f"{domain} sources rather than broader society")
        else:
            tail = f", but the supporting evidence is {ev_band}"
        return f"{parts[0]} {parts[1]}{tail}."

    def _modal_life_domain(self, claim_ids) -> str | None:
        """Human-readable modal life-domain across a theme's claims (or None)."""
        domains = [self._claim_life[c] for c in claim_ids
                   if self._claim_life.get(c)]
        if not domains:
            return None
        top = Counter(domains).most_common(1)[0][0]
        return top.replace("_", " ")

    def _filter_lived(self, lived: LivedExperience,
                      claim_index: dict[str, _ClaimRef]) -> LivedExperience:
        """Ground every lived-experience item; drop ungrounded ones, prefer
        multi-source, and cap each domain so the layer stays scannable."""
        data: dict[str, list] = {}
        for field in LivedExperience.FIELDS:
            grounded = self._filter_grounded(getattr(lived, field), claim_index)
            if grounded:
                data[field] = self._prefer_multi_source(grounded)[:MAX_LIVED_PER_DOMAIN]
        return LivedExperience(**data)

    def _filter_contradictions(self, forces: list[CompetingForce],
                               claim_index: dict[str, _ClaimRef]) -> list[CompetingForce]:
        """Keep only grounded, two-sided contradictions (paradox + explanation)."""
        grounded = self._filter_grounded(forces, claim_index)
        out = [f for f in grounded if f.pulls_toward and f.but_also]
        return out[:MAX_CONTRADICTIONS]

    def _filter_decoder(self, signals: list[CommunicationSignal],
                        claim_index: dict[str, _ClaimRef]) -> list[CommunicationSignal]:
        """Communication-decoder entries: grounded, with both phrase and meaning."""
        grounded = self._filter_grounded(signals, claim_index)
        out = [s for s in grounded if s.phrase and s.meaning]
        return self._prefer_multi_source(out)[:MAX_COMM_SIGNALS]

    def _filter_transition(self, axes: list[TransitionAxis],
                           claim_index: dict[str, _ClaimRef]) -> list[TransitionAxis]:
        """Culture-in-transition axes: grounded, with both poles described."""
        grounded = self._filter_grounded(axes, claim_index)
        out = [a for a in grounded if a.axis and (a.older or a.younger)]
        return out[:MAX_TRANSITION]

    def _filter_variations(self, variations: list[ExperienceVariation],
                           claim_index: dict[str, _ClaimRef]) -> list[ExperienceVariation]:
        """How-different-groups contrasts: grounded, with both groups + a
        difference described."""
        grounded = self._filter_grounded(variations, claim_index)
        out = [v for v in grounded if v.group_a and v.group_b and v.difference]
        return out[:MAX_EXPERIENCE_VARIATIONS]

    def _filter_life_feels_like(self, life: Observation,
                                claim_index: dict[str, _ClaimRef]) -> Observation:
        """Keep the life-feels-like narrative only when grounded (drop otherwise)."""
        if not (life and life.text):
            return Observation()
        grounded = self._filter_grounded([life], claim_index)
        return grounded[0] if grounded else Observation()

    def _filter_uniqueness(self, facets: list[UniquenessFacet],
                           claim_index: dict[str, _ClaimRef]) -> list[UniquenessFacet]:
        """Country-uniqueness facets: grounded, with a title + explanation."""
        grounded = self._filter_grounded(facets, claim_index)
        out = [f for f in grounded if f.title and f.explanation]
        return self._prefer_multi_source(out)[:MAX_UNIQUENESS]

    def _merge_dimension_takes(self, snapshot: list[DimensionSnapshot],
                               takes: list[DimensionTake],
                               claim_index: dict[str, _ClaimRef]) -> list[DimensionSnapshot]:
        """Merge grounded one-sentence dimension explanations onto the snapshot.

        A take is used only when it is grounded; otherwise the snapshot row's
        ``explanation`` falls back to its plain ``reading`` so the Cultural
        Fingerprint is never blank."""
        grounded = {t.dimension: t for t in self._filter_grounded(takes, claim_index)
                    if t.dimension is not None and t.explanation}
        for row in snapshot:
            take = grounded.get(row.dimension)
            row.explanation = take.explanation.strip() if take else (row.reading or "")
        return snapshot

    def _build_glance(self, themes: list[CulturalTheme], lived: LivedExperience,
                      newcomers: list[Observation], success: list[Observation],
                      failure: list[Observation]) -> list[str]:
        """Deterministic 'culture at a glance': 4-6 one-sentence bullets pulled
        from the strongest clustered observations (no LLM, no scores)."""
        pool: list[Observation] = []
        for t in themes:
            pool.extend(t.observations)
        for field in LivedExperience.FIELDS:
            pool.extend(getattr(lived, field))
        pool.extend(newcomers)
        pool.extend(success)
        pool.extend(failure)
        # Strongest clusters first (most corroborating sources), stable otherwise.
        pool.sort(key=lambda o: getattr(o, "sources_count", 0), reverse=True)

        bullets: list[str] = []
        seen: set[str] = set()
        for obs in pool:
            sentence = self._first_sentence(obs.text)
            if not sentence:
                continue
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            bullets.append(sentence)
            if len(bullets) >= MAX_GLANCE:
                break
        # The glance is an executive snapshot; hide it unless we have enough
        # strong material to fill the expected 4-6 bullets.
        return bullets if len(bullets) >= MIN_GLANCE else []

    @staticmethod
    def _first_sentence(text: str) -> str:
        """First sentence of an observation, trimmed to a single clean line."""
        t = " ".join((text or "").split()).strip()
        if not t:
            return ""
        m = re.search(r"[.!?](\s|$)", t)
        sentence = t[: m.start() + 1] if m else t
        return sentence.strip()

    def _filter_friendship(self, fmap: FriendshipMap,
                           claim_index: dict[str, _ClaimRef]) -> FriendshipMap:
        """Ground each friendship facet; reset ungrounded facets to empty so the
        UI hides them (a facet needs a label AND a resolvable claim)."""
        data: dict[str, FriendshipFacet] = {}
        for field in FriendshipMap.FIELDS:
            facet = getattr(fmap, field)
            if not facet.label:
                continue
            grounded = self._filter_grounded([facet], claim_index)
            if grounded:
                data[field] = grounded[0]
        return FriendshipMap(**data)

    def _filter_archetype(self, archetype: Archetype,
                          claim_index: dict[str, _ClaimRef]) -> Archetype:
        """Keep the archetype only when it has a title AND a resolvable claim."""
        if not archetype.title:
            return Archetype()
        grounded = self._filter_grounded([archetype], claim_index)
        return grounded[0] if grounded else Archetype()

    def _merge_similar(self, seed: list[SimilarCulture],
                       drafted: list[SimilarCulture],
                       claim_index: dict[str, _ClaimRef]) -> list[SimilarCulture]:
        """Attach grounded LLM explanations onto the deterministic similar set,
        matched by iso3. The country set stays fixed; an explanation is kept only
        when grounded, otherwise the entry remains (country + similarity only)."""
        by_iso: dict[str, SimilarCulture] = {}
        for s in self._filter_grounded(drafted, claim_index):
            if s.iso3 and s.explanation:
                by_iso[s.iso3.upper()] = s
        out: list[SimilarCulture] = []
        for entry in seed:
            match = by_iso.get(entry.iso3.upper())
            if match:
                entry.explanation = match.explanation
                entry.claim_ids = match.claim_ids
                entry.sources_count = match.sources_count
            out.append(entry)
        return out

    @staticmethod
    def _prefer_multi_source(items):
        """Sort multi-source items first; when any multi-source item exists, drop
        single-source ones (the clustering rule: single-source should be rare).
        Never returns empty when the input was non-empty."""
        ordered = sorted(items, key=lambda i: getattr(i, "sources_count", 0), reverse=True)
        multi = [i for i in ordered if getattr(i, "sources_count", 0) >= 2]
        return multi if multi else ordered

    def _modal_dimension(self, claim_ids) -> Dimension | None:
        """The dimension most of a theme's backing claims speak to (for the
        expert/framework agreement components of theme confidence)."""
        dims = [self._claim_dim[c] for c in claim_ids
                if self._claim_dim.get(c) is not None]
        if not dims:
            return None
        return Counter(dims).most_common(1)[0][0]

    @staticmethod
    def _filter_grounded(items, claim_index: dict[str, _ClaimRef]):
        """Drop items with no resolvable claim_ids; compute their sources_count."""
        survivors = []
        for item in items:
            resolved = [c for c in item.claim_ids if c in claim_index]
            if not resolved:
                continue
            item.claim_ids = resolved
            item.sources_count = len({claim_index[c].source_id
                                      for c in resolved if claim_index[c].source_id})
            survivors.append(item)
        return survivors

    @staticmethod
    def _clean_good_for(values: list[str]) -> list[str]:
        """Country-specific use cases: short, de-duplicated free text (no fixed
        vocabulary), so the list can be tailored to each country."""
        out: list[str] = []
        seen: set[str] = set()
        for v in values:
            text = " ".join(str(v).split()).strip(" .")
            if not text or len(text) > 60:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(text)
        return out[:MAX_GOOD_FOR]
