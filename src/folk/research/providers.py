"""ResearchProvider abstraction: provider-native web research producing a
single-origin SpecialistEvidencePack + SpecialistAssessment per seat.

- DeterministicResearchProvider: offline/mock only. Builds a reproducible pack
  from canonical framework citations + the knowledge pack. Used by the test
  suite; never a live fallback.
- OpenAIResearchProvider / AnthropicResearchProvider / DeepSeekResearchProvider:
  live native web search (Responses web_search / Messages web_search server tool
  / DeepSeek's Anthropic-compatible endpoint). On any capability failure they
  raise ResearchCapabilityError - the system never substitutes a search backend.
"""

from __future__ import annotations

import hashlib
import json

from folk.config import get_settings
from folk.llm.base import LLMError, extract_json
from folk.models.enums import DIMENSIONS, Dimension, SourceCategory
from folk.models.evidence import DimensionEvidence
from folk.models.knowledge import CountryKnowledgePack
from folk.models.research import (
    EvidenceCitation,
    EvidenceClaim,
    EvidenceSource,
    SpecialistAssessment,
    SpecialistDimensionView,
    SpecialistEvidencePack,
)
from folk.reference.canonical import references_for_frameworks
from folk.research.dimension_guide import DIMENSION_CHEAT_SHEET
from folk.research.errors import ResearchCapabilityError
from folk.research.seats import SeatAssignment
from folk.research.verification import score_source
from folk.utils.logging import get_logger

log = get_logger()

ANCHOR = 50.0

# Canonical lived-experience domains shared by the research prompt and the
# culture-first profile's lived-experience + practical layers. The first block
# feeds the "what you would experience" buckets + status/mistakes sections; the
# second block feeds the dedicated success/failure/decoder/transition sections.
LIFE_DOMAINS = (
    "daily_life", "workplace", "communication", "friendship_social",
    "society", "social_mistakes", "status_signals",
    "success_factor", "failure_factor", "communication_decoder", "cultural_transition",
)

# Concrete, dimension-anchored sentences for the deterministic provider so that
# mock/offline runs (and the test suite) never emit score-restatement templates
# like "X's Identity sits near 74". Keyed by (dimension, leans_high).
_MOCK_DIM_CLAIM: dict[tuple[str, bool], str] = {
    ("D1", True): ("In {country}, people are generally expected to make major life choices - "
                   "career, partner, where to live - as individuals rather than deferring to "
                   "family or group consensus."),
    ("D1", False): ("In {country}, family and in-group expectations weigh heavily on major "
                    "personal decisions, and visibly breaking from the group carries a social cost."),
    ("D2", True): ("Open displays of feeling and direct disagreement are common and broadly "
                   "accepted in {country}'s everyday and public life."),
    ("D2", False): ("People in {country} tend to keep strong feelings private and signal "
                    "disagreement indirectly rather than stating it openly."),
    ("D3", True): ("Daily life in {country} runs on clear rules, schedules, and predictable "
                   "procedures, and unplanned ambiguity is treated as uncomfortable."),
    ("D3", False): ("People in {country} are comfortable improvising and living with ambiguity "
                    "rather than holding to rigid plans and fixed rules."),
    ("D4", True): ("Achievement, education, and visible success are powerful social motivators "
                   "in {country}."),
    ("D4", False): ("In {country}, balance and contentment are prized over relentless "
                    "competition or status-seeking."),
}

# Concrete lived-experience sentences for the deterministic provider, keyed by
# life domain. Mock-only: live runs gather these from real web evidence.
_MOCK_LIFE_CLAIM: dict[str, str] = {
    "daily_life": ("Everyday routines in {country} - shopping, transport, meals - run on widely "
                   "shared rhythms that newcomers are expected to pick up quickly."),
    "workplace": ("In {country} workplaces, seniority and clearly defined roles shape who "
                  "speaks first in meetings and how decisions are escalated."),
    "communication": ("Newcomers to {country} often misread how directly criticism and refusal "
                      "are expressed, and have to learn the local way of saying 'no'."),
    "friendship_social": ("Close friendships in {country} tend to form slowly and then run deep, "
                          "with clear expectations about reciprocity and showing up."),
    "society": ("Public life in {country} reflects strong shared expectations about order, "
                "fairness, and how strangers treat one another."),
    "social_mistakes": ("A common social misstep in {country} is being too familiar too quickly "
                        "with people who are older or more senior."),
    "status_signals": ("In {country}, education, job title, and the institutions one is affiliated "
                       "with are read as important markers of social standing."),
    "success_factor": ("People tend to get ahead in {country} by being well prepared, reliable, "
                       "and consistent rather than by self-promotion."),
    "failure_factor": ("A frequent cause of friction in {country} is over-promising and failing "
                       "to follow through on commitments."),
    "communication_decoder": ("When people in {country} say a request 'might be difficult', they "
                              "usually mean no rather than maybe."),
    "cultural_transition": ("Younger and urban {country} residents are noticeably more individualistic "
                            "and informal than older or rural generations."),
}


def _short_hash(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:8]


def _base_value(pack: CountryKnowledgePack, dim: Dimension) -> float:
    b = pack.baselines[dim].baseline if dim in pack.baselines else None
    if b is not None:
        return b
    rm = getattr(pack.regional_context, f"mean_{dim.field}", None)
    return rm if rm is not None else ANCHOR


def _seat_proposed(seat_value: str, pack: CountryKnowledgePack, dim: Dimension,
                   evidence: dict[Dimension, DimensionEvidence]) -> float:
    """Deterministic per-seat proposal that intentionally diverges so the three
    seats disagree (driving the integrator's disagreement-scaled influence)."""
    base = _base_value(pack, dim)
    s = get_settings()
    if seat_value == "cultural_anthropologist":
        push = 0.0
        de = evidence.get(dim)
        if de:
            for it in de.items:
                if it.direction == "supports_high":
                    push += 1.6 * it.weight
                elif it.direction == "supports_low":
                    push -= 1.6 * it.weight
        val = base + max(-6.0, min(6.0, push))
    elif seat_value == "institutional_analyst":
        sig = pack.framework_signals.get(dim)
        if sig and sig.consensus is not None:
            val = 0.65 * base + 0.35 * sig.consensus
        else:
            val = base
    else:  # historical_analyst
        rm = getattr(pack.regional_context, f"mean_{dim.field}", None)
        val = 0.55 * base + 0.45 * rm if rm is not None else base
    return float(max(s.score_min, min(s.score_max, round(val, 1))))


class BaseResearchProvider:
    """Contract: research one seat for one country -> single-origin pack."""

    name = "base"

    def research(
        self,
        assignment: SeatAssignment,
        pack: CountryKnowledgePack,
        evidence: dict[Dimension, DimensionEvidence],
        *,
        extra_lenses: list[str] | None = None,
    ) -> tuple[SpecialistEvidencePack, SpecialistAssessment]:
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Deterministic (mock / offline) provider
# --------------------------------------------------------------------------- #
class DeterministicResearchProvider(BaseResearchProvider):
    name = "deterministic"

    def __init__(self, provider_label: str = "deterministic") -> None:
        # provider_label lets mock packs still record the assigned provider name.
        self.provider_label = provider_label

    def research(self, assignment, pack, evidence, *, extra_lenses=None):
        seat = assignment.seat
        provider = assignment.provider or self.provider_label
        persona = assignment.persona
        iso = pack.iso3

        sources: list[EvidenceSource] = []
        claims: list[EvidenceClaim] = []
        citations: list[EvidenceCitation] = []
        dim_views: dict[Dimension, SpecialistDimensionView] = {}

        # Real anchor sources: the canonical framework citations for this country.
        for ref in references_for_frameworks(pack.framework_coverage):
            sid = f"S_{iso}_{seat.value}_{_short_hash(provider, ref.citation)}"
            cat = (SourceCategory.PEER_REVIEWED_PAPER
                   if "journal" in ref.source_type.value
                   else SourceCategory.BOOK)
            src = score_source(EvidenceSource(
                source_id=sid, title=ref.citation, url=ref.url_or_doi,
                source_category=cat, source_type=ref.source_type,
                provider_discovered_by=provider,
            ), verify=False)
            sources.append(src)

        primary_cat = persona.preferred_categories[0]
        for d in DIMENSIONS:
            proposed = _seat_proposed(seat.value, pack, d, evidence)
            direction = "supports_high" if proposed >= ANCHOR else "supports_low"

            sid = f"S_{iso}_{seat.value}_{d.value}_{_short_hash(provider, d.value)}"
            url = f"https://example-research.org/{iso.lower()}/{seat.value}/{d.value.lower()}"
            src = score_source(EvidenceSource(
                source_id=sid,
                title=f"{persona.title} reading of {pack.country} {d.label}",
                url=url, author=persona.title, publication_year=2020,
                source_category=primary_cat, source_type=primary_cat.source_type,
                provider_discovered_by=provider,
            ), verify=False)
            sources.append(src)

            # Claim confidence tracks the underlying framework signal strength so
            # thinly/conflicting-evidenced countries yield genuinely weaker
            # corroboration (rather than uniformly strong synthetic support).
            sig = pack.framework_signals.get(d)
            signal_strength = float(sig.signal_strength) if sig else 0.0
            claim_conf = round(0.3 + 0.45 * signal_strength, 3)

            leans_high = proposed >= ANCHOR
            cid = f"C_{iso}_{seat.value}_{d.value}"
            claim_text = _MOCK_DIM_CLAIM[(d.value, leans_high)].format(country=pack.country)
            claims.append(EvidenceClaim(
                claim_id=cid, source_id=sid, claim=claim_text,
                supporting_dimension=d, support_direction=direction,
                confidence=claim_conf,
            ))
            citations.append(EvidenceCitation(
                claim_id=cid, source_id=sid, title=src.title, url=url,
                author=persona.title, publication_year=2020, excerpt=claim_text,
                dimension=d, support_direction=direction,
            ))

            # A concrete opposing observation (confirmation-bias guard): the real
            # countercurrent that pulls the other way, stated as a fact - never a
            # "counter-consideration" boilerplate line.
            counter_id = f"CC_{iso}_{seat.value}_{d.value}"
            counter_dir = "supports_low" if direction == "supports_high" else "supports_high"
            counter_text = ("A visible countercurrent runs the other way: "
                            + _MOCK_DIM_CLAIM[(d.value, not leans_high)].format(
                                country=pack.country)[0].lower()
                            + _MOCK_DIM_CLAIM[(d.value, not leans_high)].format(
                                country=pack.country)[1:])
            claims.append(EvidenceClaim(
                claim_id=counter_id, source_id=sid, claim=counter_text,
                supporting_dimension=d, support_direction=counter_dir,
                confidence=round(claim_conf * 0.6, 3),
            ))

            dim_views[d] = SpecialistDimensionView(
                dimension=d, proposed_score=proposed,
                supporting_evidence=[cid], counter_evidence=[counter_id],
                cultural_rationale=(
                    f"{persona.title}: {pack.country} {d.label}={proposed:.0f} via "
                    f"{persona.research_strategy}."),
                confidence=round(0.5 + 0.05 * len(pack.framework_coverage), 3),
            )

        # Lived-experience claims (what a newcomer would actually notice): one
        # per domain, grounded in a dedicated source so the culture-first
        # profile's lived-experience layer is populated even on mock runs.
        for domain in LIFE_DOMAINS:
            sid = f"S_{iso}_{seat.value}_life_{domain}_{_short_hash(provider, domain)}"
            url = f"https://example-research.org/{iso.lower()}/{seat.value}/life/{domain}"
            sources.append(score_source(EvidenceSource(
                source_id=sid,
                title=f"{persona.title} field notes on {pack.country} {domain.replace('_', ' ')}",
                url=url, author=persona.title, publication_year=2021,
                source_category=primary_cat, source_type=primary_cat.source_type,
                provider_discovered_by=provider,
            ), verify=False))
            cid = f"C_{iso}_{seat.value}_life_{domain}"
            life_text = _MOCK_LIFE_CLAIM[domain].format(country=pack.country)
            claims.append(EvidenceClaim(
                claim_id=cid, source_id=sid, claim=life_text,
                support_direction="neutral", confidence=0.6, life_domain=domain,
            ))
            citations.append(EvidenceCitation(
                claim_id=cid, source_id=sid, title=sources[-1].title, url=url,
                author=persona.title, publication_year=2021, excerpt=life_text))

        queries = [f"{pack.country} {d.label} {persona.focus[0]}" for d in DIMENSIONS]
        queries += [f"{pack.country} {domain.replace('_', ' ')} norms" for domain in LIFE_DOMAINS]
        if extra_lenses:
            queries += [f"{pack.country} {lens}" for lens in extra_lenses]

        epack = SpecialistEvidencePack(
            iso3=iso, seat=seat, provider=provider, search_queries=queries,
            sources=sources, claims=claims, citations=citations,
            confidence_summary=round(
                sum(v.confidence for v in dim_views.values()) / len(dim_views), 3),
            notes=f"{persona.title} ({provider}) deterministic research.",
        )
        assessment = SpecialistAssessment(
            iso3=iso, seat=seat, provider=provider, dimensions=dim_views,
            summary=f"{persona.title} ({provider}) assessment of {pack.country}.")
        return epack, assessment


# --------------------------------------------------------------------------- #
# Live native-web-search providers
# --------------------------------------------------------------------------- #
class _LiveResearchProvider(BaseResearchProvider):
    """Shared scaffold for native-web-search providers.

    Subclasses implement `_research_complete(system, user) -> raw_text` using
    their provider's native web-search tool. On any capability failure they must
    raise ResearchCapabilityError (no fallback)."""

    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.api_key = api_key
        self.settings = get_settings()

    def _research_complete(self, system: str, user: str) -> str:
        raise NotImplementedError

    def research(self, assignment, pack, evidence, *, extra_lenses=None):
        persona = assignment.persona
        # The dimension cheat sheet rides in the system prompt so every seat reads
        # "what each dimension is and is NOT" before scoring - stopping the D3->D1
        # conflation (orderly read as collectivist) at the source.
        system = f"{persona.system_prompt}\n\n{DIMENSION_CHEAT_SHEET}"
        user = self._build_prompt(persona, pack, extra_lenses)
        try:
            payload = self._research_payload(system, user)
        except ResearchCapabilityError:
            raise
        except Exception as exc:  # noqa: BLE001
            # A transient stall (request timeout, dropped connection, provider
            # overload) should not silently cost a whole seat - retry ONCE before
            # giving up, then fail rather than fabricate a contaminated pack.
            if self._is_transient(exc):
                log.warning(
                    f"{self.name}: {pack.iso3}/{assignment.seat.value} research call failed "
                    f"transiently ({exc}); retrying once.")
                try:
                    payload = self._research_payload(system, user)
                except Exception as exc2:  # noqa: BLE001
                    raise ResearchCapabilityError(
                        self.name,
                        f"native research failed for {pack.iso3}/{assignment.seat.value} "
                        f"after one retry: {exc2}") from exc2
            else:
                # We cannot fabricate real research; failing is preferable to a
                # silent, contaminated pack.
                raise ResearchCapabilityError(
                    self.name,
                    f"native research failed for {pack.iso3}/{assignment.seat.value}: {exc}"
                ) from exc
        epack, assessment = self._assemble(assignment, pack, payload)
        # A parseable-but-evidence-empty response (the model answered from memory in
        # a few seconds instead of really searching) leaves the seat with ZERO usable
        # recommendations - its input is effectively MISSING from the deliberation.
        # Re-prompt ONCE, forcing genuine web research, rather than silently
        # contributing nothing. Keep whichever attempt yields more backed dimensions.
        if self._backed_count(assessment) == 0:
            log.warning(
                f"{self.name}: seat '{assignment.seat.value}' for {pack.iso3} returned no "
                "evidence-backed dimensions; re-prompting once for genuine web research.")
            retry_user = (
                f"{user}\n\nYour previous response contained NO citable claims and scored no "
                "dimension with evidence, so it is unusable. You MUST actually perform web "
                "searches, read real sources, emit a NON-EMPTY \"claims\" array, and reference "
                "those claim_ids in each dimension's \"supporting_evidence\"/\"counter_evidence\". "
                "Abstain on a dimension ONLY when you genuinely cannot evidence it - never on all four."
            )
            try:
                retry_payload = self._research_payload(system, retry_user)
                r_epack, r_assessment = self._assemble(assignment, pack, retry_payload)
                if self._backed_count(r_assessment) > self._backed_count(assessment):
                    return r_epack, r_assessment
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    f"{self.name}: re-prompt for {pack.iso3}/{assignment.seat.value} "
                    f"failed ({exc}); keeping first result.")
            return epack, assessment
        # Self-consistency re-prompt (bounded to ONE extra call): a scored view that
        # contradicts its own cited evidence (e.g. cites individualist evidence yet
        # scores collectivist) is a hard reasoning error. Re-prompt once, quoting the
        # contradiction, and keep the retry only if it removes contradictions without
        # losing evidence-backed dimensions.
        contradictions = self._contradiction_count(assessment)
        if contradictions:
            notes = "; ".join(
                f"{d.value}: {v.consistency_note}"
                for d, v in assessment.dimensions.items()
                if v.has_recommendation and not v.self_consistent)
            log.warning(
                f"{self.name}: seat '{assignment.seat.value}' for {pack.iso3} produced "
                f"{contradictions} self-inconsistent score(s); re-prompting once.")
            retry_user = (
                f"{user}\n\nYour previous response contained a SELF-CONSISTENCY error: {notes}. "
                "Re-check each flagged dimension: anchor on the strongest measured signal, route "
                "each piece of evidence to the dimension it actually belongs to (rules/order/"
                "conformity are Structure, not Identity), and make the score match the direction "
                "of the evidence you cite. Cite the number, then match the score to it."
            )
            try:
                retry_payload = self._research_payload(system, retry_user)
                r_epack, r_assessment = self._assemble(assignment, pack, retry_payload)
                if (self._contradiction_count(r_assessment) < contradictions
                        and self._backed_count(r_assessment) >= self._backed_count(assessment)):
                    return r_epack, r_assessment
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    f"{self.name}: self-consistency re-prompt for "
                    f"{pack.iso3}/{assignment.seat.value} failed ({exc}); keeping first result.")
        return epack, assessment

    @staticmethod
    def _backed_count(assessment: SpecialistAssessment) -> int:
        return sum(1 for v in assessment.dimensions.values() if v.has_recommendation)

    # A score must sit at least this far from the 50 anchor to count as decisively
    # placed. Mildly-placed scores (35-65) reflect genuinely mixed evidence and are
    # NEVER treated as contradictions - every seat is REQUIRED to gather counter-
    # evidence, so a near-anchor score with more counter than supporting claims is
    # expected, not an error.
    _CONSISTENCY_MARGIN = 15.0
    # ...and even for a decisive score, the OPPOSING evidence must be a clear
    # majority (>= this share of the directional claims) before it is a
    # contradiction, so the mandatory minority counter-evidence cannot trip it.
    _CONSISTENCY_OPPOSING_SHARE = 0.67

    @classmethod
    def _flag_self_inconsistency(cls, dim_views, by_id, iso3: str, seat) -> None:
        """Flag any DECISIVELY-placed view whose own cited evidence is a clear
        majority pointing the OTHER way (the Germany D1=30-with-individualist-
        evidence failure mode). Sets ``self_consistent``/``consistency_note`` in
        place; never changes the score. Mildly-placed or mixed-evidence scores are
        left alone - gathering counter-evidence is mandatory, not a contradiction."""
        for d, view in dim_views.items():
            if view.abstained or view.proposed_score is None:
                continue
            score = float(view.proposed_score)
            if abs(score - ANCHOR) < cls._CONSISTENCY_MARGIN:
                continue  # mildly placed -> mixed evidence is legitimate
            high = low = 0
            for cid in list(view.supporting_evidence) + list(view.counter_evidence):
                claim = by_id.get(cid)
                if claim is None:
                    continue
                if claim.support_direction == "supports_high":
                    high += 1
                elif claim.support_direction == "supports_low":
                    low += 1
            directional = high + low
            if directional == 0:
                continue  # no directional evidence -> nothing to contradict
            if score >= ANCHOR:
                opposing, opp_lean = low, "low"
            else:
                opposing, opp_lean = high, "high"
            # Only a decisive opposing MAJORITY is a contradiction (e.g. a score of
            # 30/collectivist while >=2/3 of the cited evidence is individualist).
            if opposing / directional < cls._CONSISTENCY_OPPOSING_SHARE:
                continue
            view.self_consistent = False
            view.consistency_note = (
                f"Score {score:.0f} sits on the "
                f"{'high' if score >= ANCHOR else 'low'} side of 50 but "
                f"{opposing}/{directional} of the cited directional evidence leans "
                f"{opp_lean}. Cite the number, then match the score to it.")
            log.warning(
                f"{cls.name}: seat '{getattr(seat, 'value', seat)}' for {iso3} {d.value}: "
                f"{view.consistency_note}")

    @classmethod
    def _contradiction_count(cls, assessment: SpecialistAssessment) -> int:
        return sum(1 for v in assessment.dimensions.values()
                   if v.has_recommendation and not v.self_consistent)

    # Substrings that mark a retryable, non-deterministic provider failure (a
    # stalled request, dropped connection, or transient overload) - as opposed to
    # a genuine capability/parse error, which should not be retried.
    _TRANSIENT_MARKERS = (
        "timed out", "timeout", "connection", "overloaded",
        "temporarily unavailable", "rate limit", "429", "503", "529",
    )

    @classmethod
    def _is_transient(cls, exc: Exception) -> bool:
        text = f"{type(exc).__name__} {exc}".lower()
        return any(marker in text for marker in cls._TRANSIENT_MARKERS)

    def _research_payload(self, system: str, user: str) -> dict:
        """Run native research and parse JSON, re-prompting once if the first
        response cannot be parsed (no JSON / malformed beyond repair)."""
        raw = self._research_complete(system, user)
        try:
            return extract_json(raw)
        except LLMError as exc:
            log.warning(f"{self.name}: first response unparseable ({exc}); "
                        f"raw response head: {self._snippet(raw)}")
            repair = (
                f"{user}\n\nYour previous response could not be parsed as JSON ({exc}). "
                "Respond again with a SINGLE valid JSON object ONLY - no prose, no "
                "markdown, no commentary before or after the object."
            )
            raw = self._research_complete(system, repair)
            try:
                return extract_json(raw)
            except LLMError as exc2:
                log.error(f"{self.name}: repair response also unparseable ({exc2}); "
                          f"raw response head: {self._snippet(raw)}")
                raise

    @staticmethod
    def _snippet(text: str, limit: int = 400) -> str:
        t = (text or "").strip().replace("\n", " ")
        return (t[:limit] + " ...") if len(t) > limit else t

    def _build_prompt(self, persona, pack: CountryKnowledgePack,
                      extra_lenses: list[str] | None) -> str:
        lenses = ""
        if extra_lenses:
            lenses = ("\nThis country shows a compressed profile - explicitly investigate "
                      "genuine differentiation via: " + ", ".join(extra_lenses) + ".")
        dims = ", ".join(f"{d.value}={d.label} ({d.low_pole}<->{d.high_pole})" for d in DIMENSIONS)
        return (
            f"Research {pack.country} ({pack.iso3}). Strategy: {persona.research_strategy}.{lenses}\n"
            f"For EACH FOLK dimension [{dims}] find supporting AND counter evidence from real, "
            "citable web sources, then propose a 3-97 score.\n"
            "DIMENSION ROUTING (critical - read the cheat sheet in your system prompt first): before "
            "any piece of evidence changes a score, decide which SINGLE dimension it actually "
            "belongs to, and tag its claim's `supporting_dimension` to THAT dimension only. Evidence "
            "about one dimension must NOT move another dimension's score. In particular: "
            "rules/order/punctuality/conformity/'strong institutions'/discomfort-with-ambiguity are "
            "D3 Structure, NEVER D1 Identity - a country can be individualist AND orderly at once "
            "(Germany). Directness/bluntness is not D2 openness. Governance quality / rule of law is "
            "not any dimension. Do not tag a Structure observation to D1.\n"
            "ANCHOR ON THE STRONGEST MEASURED SIGNAL: start each dimension from its best-established "
            "measure (e.g. the Hofstede index for that dimension - Individualism for D1, Masculinity "
            "for D4) and let country-specific exceptions ADJUST the score, never FLIP its direction. "
            "A single colourful counter-example nudges the score; it does not invert it.\n"
            "SELF-CONSISTENCY (mandatory before you submit): if the main figure you cite points one "
            "way but your score points the other, stop and re-check. Citing 'Individualism = 67' "
            "(individualist) and then proposing a score of 30 (collectivist) is a contradiction that "
            "must NEVER be submitted. Cite the number, then match the score to it.\n"
            "EVIDENCE-QUALITY FLOOR: do not rest a score entirely on sources you mark 'unverified'. "
            "Require at least one solid, corroborated source - especially when your score deviates "
            "far from what the framework baseline would suggest; a large deviation needs strong "
            "evidence, not weak evidence.\n"
            "CORROBORATION (important): for each MAJOR cultural pattern you assert, try to gather "
            "2+ INDEPENDENT sources rather than a single citation. Emit a separate claim (with its "
            "own source) for each corroborating source, but keep their `claim` text describing the "
            "SAME pattern so the profile writer can cluster them into one well-supported insight. "
            "Multi-source patterns are far more valuable than many isolated single-source facts.\n"
            "EVIDENCE BREADTH: draw on a BROAD, attributable base where available - peer-reviewed "
            "work AND books, ethnographies, country/area studies, historical analyses, "
            "institutional/IGO reports, long-form journalism, and credible cultural commentary. Do "
            "NOT rely on cross-country surveys or framework datasets alone; those compress toward "
            "the global mean and hide what makes this country distinctive. Every source must remain "
            "real, citable, and verifiable.\n"
            "ALSO gather LIVED-EXPERIENCE evidence: concrete, citable findings about what a "
            "newcomer would actually notice and need to navigate. Tag each such claim with a "
            "\"life_domain\" from exactly: daily_life, workplace, communication, friendship_social, "
            "society, social_mistakes, status_signals, success_factor, failure_factor, "
            "communication_decoder, cultural_transition. Use these tags as follows: "
            "success_factor = what makes people get ahead/succeed here; failure_factor = the "
            "mistakes that create friction or fail here; communication_decoder = a literal local "
            "phrase and what it ACTUALLY means (only if you find real evidence of the phrase); "
            "cultural_transition = how a norm differs older-vs-younger or urban-vs-rural. "
            "Prefer specifics that DISTINGUISH this country (e.g. how disagreement is voiced, how "
            "friendships form, what social mistakes to avoid, what signals status) over generic "
            "statements true of most countries. Never invent a phrase or a generational shift; "
            "leave a tag unused rather than fabricate.\n"
            "CRITICAL OUTPUT ORDER: emit the \"dimensions\" array FIRST and complete it for ALL "
            "FOUR dimensions [D1, D2, D3, D4] before listing sources and claims - never omit or "
            "truncate a dimension. If, after genuine research, you have NO citable evidence for a "
            "dimension, set its \"proposed_score\" to null and \"abstained\" to true rather than "
            "guessing a midpoint; never emit a placeholder score with empty evidence.\n"
            "Return JSON ONLY with this shape: {\"dimensions\":["
            "{\"dimension\":\"D1\",\"proposed_score\":50,\"abstained\":false,"
            "\"supporting_evidence\":[\"claim_id\"],\"counter_evidence\":[\"claim_id\"],"
            "\"cultural_rationale\":\"\",\"confidence\":0.7}],"
            "\"search_queries\":[...],\"sources\":["
            "{\"source_id\":\"\",\"title\":\"\",\"url\":\"\",\"author\":\"\",\"publication_year\":2020,"
            "\"source_category\":\"peer_reviewed_paper\"}],\"claims\":[{\"claim_id\":\"\","
            "\"source_id\":\"\",\"claim\":\"\",\"supporting_dimension\":\"D1\","
            "\"support_direction\":\"supports_high\",\"confidence\":0.7,\"life_domain\":null}]}"
        )

    def _assemble(self, assignment, pack, payload: dict):
        provider = assignment.provider
        seat = assignment.seat
        sources = []
        for s in payload.get("sources", []):
            try:
                sources.append(score_source(EvidenceSource.model_validate(
                    {**s, "provider_discovered_by": provider})))
            except Exception as exc:  # noqa: BLE001
                log.warning(f"{self.name}: skipping invalid source ({exc}); "
                            f"raw: {self._snippet(str(s), 200)}")
        claims = []
        for c in payload.get("claims", []):
            try:
                claims.append(EvidenceClaim.model_validate(c))
            except Exception as exc:  # noqa: BLE001
                log.warning(f"{self.name}: skipping invalid claim ({exc}); "
                            f"raw: {self._snippet(str(c), 200)}")
        by_id = {c.claim_id: c for c in claims}
        src_by_id = {s.source_id: s for s in sources}
        citations: list[EvidenceCitation] = []
        for c in claims:
            s = src_by_id.get(c.source_id)
            citations.append(EvidenceCitation(
                claim_id=c.claim_id, source_id=c.source_id,
                title=s.title if s else "", url=s.url if s else None,
                author=s.author if s else None,
                publication_year=s.publication_year if s else None,
                excerpt=c.claim, dimension=c.supporting_dimension,
                support_direction=c.support_direction))
        dim_views: dict[Dimension, SpecialistDimensionView] = {}
        for dv in payload.get("dimensions", []):
            try:
                view = SpecialistDimensionView.model_validate(dv)
            except Exception as exc:  # noqa: BLE001
                log.warning(f"{self.name}: skipping invalid dimension view ({exc}); "
                            f"raw: {self._snippet(str(dv), 200)}")
                continue
            if view.dimension is not None:
                dim_views[view.dimension] = view
        # Any dimension the seat did not return (or returned without evidence) is an
        # explicit ABSTENTION, never a synthetic midpoint. Downstream aggregation
        # ignores abstentions so a silent seat cannot pull the score to the centre.
        for d in DIMENSIONS:
            dim_views.setdefault(d, SpecialistDimensionView(dimension=d, abstained=True))
        # SALVAGE: a model sometimes scores a dimension (proposed_score set, not
        # abstained) yet forgets to copy the relevant claim_ids into the view's
        # evidence lists - which wrongly demotes a real, evidence-backed view to an
        # abstention and silently drops the seat's input. Re-link the seat's OWN
        # claims tagged to that dimension (real evidence it already gathered - never
        # fabricated) so the recommendation is counted. A claim's own support
        # direction decides whether it lands in the supporting or counter ledger.
        claims_by_dim: dict[Dimension, dict[str, list[str]]] = {}
        for c in claims:
            if c.supporting_dimension is None:
                continue
            bucket = claims_by_dim.setdefault(
                c.supporting_dimension, {"support": [], "counter": []})
            key = "counter" if c.support_direction == "supports_low" else "support"
            bucket[key].append(c.claim_id)
        for d, view in dim_views.items():
            if (not view.abstained and view.proposed_score is not None
                    and not view.supporting_evidence and not view.counter_evidence
                    and d in claims_by_dim):
                view.supporting_evidence = list(claims_by_dim[d]["support"])
                view.counter_evidence = list(claims_by_dim[d]["counter"])
        # Self-consistency: a view whose score contradicts the direction its OWN
        # cited evidence points (e.g. cites individualist evidence, scores
        # collectivist) is flagged - the Germany D1=30 failure mode.
        self._flag_self_inconsistency(dim_views, by_id, pack.iso3, seat)
        backed = sum(1 for v in dim_views.values() if v.has_recommendation)
        if backed < len(DIMENSIONS):
            log.warning(
                f"{self.name}: seat '{seat.value}' for {pack.iso3} produced "
                f"{backed}/{len(DIMENSIONS)} evidence-backed dimensions "
                f"({len(DIMENSIONS) - backed} abstained). Raw dimensions parsed: "
                f"{len(payload.get('dimensions', []))}.")
        epack = SpecialistEvidencePack(
            iso3=pack.iso3, seat=seat, provider=provider,
            search_queries=[str(q) for q in payload.get("search_queries", [])],
            sources=sources, claims=claims, citations=citations,
            confidence_summary=round(
                sum(v.confidence for v in dim_views.values()) / max(1, len(dim_views)), 3),
            notes=f"{seat.label} ({provider}) native web research.")
        assessment = SpecialistAssessment(
            iso3=pack.iso3, seat=seat, provider=provider, dimensions=dim_views,
            summary=f"{seat.label} ({provider}) assessment of {pack.country}.")
        return epack, assessment


class OpenAIResearchProvider(_LiveResearchProvider):
    name = "openai"

    def _research_complete(self, system: str, user: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise ResearchCapabilityError(self.name, "openai SDK not installed") from exc
        client = OpenAI(
            api_key=self.api_key,
            timeout=self.settings.research_call_timeout_seconds,
            max_retries=0,
        )
        # Native web search via the Responses API hosted tool.
        resp = client.responses.create(
            model=self.model,
            tools=[{"type": "web_search"}],
            input=f"{system}\n\n{user}",
        )
        text = getattr(resp, "output_text", None)
        if not text:
            raise ResearchCapabilityError(self.name, "empty web_search response")
        return text


class AnthropicResearchProvider(_LiveResearchProvider):
    name = "anthropic"
    web_tool_version = "web_search_20250305"
    base_url: str | None = None

    def _research_complete(self, system: str, user: str) -> str:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ResearchCapabilityError(self.name, "anthropic SDK not installed") from exc
        kwargs = {
            "api_key": self.api_key,
            "timeout": self.settings.research_call_timeout_seconds,
            "max_retries": 0,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = anthropic.Anthropic(**kwargs)
        resp = client.messages.create(
            model=self.model,
            max_tokens=getattr(self.settings, "research_max_tokens", 8000),
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{"type": self.web_tool_version, "name": "web_search",
                    "max_uses": getattr(self.settings, "research_max_uses", 5)}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content)
        if not text:
            raise ResearchCapabilityError(self.name, "empty web_search response")
        return text


class DeepSeekResearchProvider(AnthropicResearchProvider):
    """DeepSeek seat on its Anthropic-compatible endpoint.

    DeepSeek's API does NOT host Anthropic's `web_search` server tool, so this
    seat runs as a knowledge/reasoning analyst: it answers from the model's
    trained knowledge of scholarly literature (no live web search). Sources it
    cites therefore stay UNVERIFIED unless independently resolved downstream.
    """

    name = "deepseek"

    def __init__(self, model: str, api_key: str, base_url: str) -> None:
        super().__init__(model, api_key)
        self.base_url = base_url

    def _research_complete(self, system: str, user: str) -> str:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ResearchCapabilityError(self.name, "anthropic SDK not installed") from exc
        client = anthropic.Anthropic(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.settings.research_call_timeout_seconds,
            max_retries=0,
        )
        # No web_search tool: DeepSeek's proxy ignores it and replies in prose.
        # Run as a knowledge analyst and require a JSON-only answer.
        knowledge_system = (
            f"{system}\n\nYou do NOT have live web access. Answer from your trained "
            "knowledge of the scholarly and cultural literature. Cite the most "
            "authoritative sources you can recall (author/title/year); do not fabricate URLs."
        )
        resp = client.messages.create(
            model=self.model,
            max_tokens=getattr(self.settings, "research_max_tokens", 8000),
            system=knowledge_system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content)
        if not text:
            raise ResearchCapabilityError(self.name, "empty response")
        return text
