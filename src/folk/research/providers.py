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
from folk.research.errors import ResearchCapabilityError
from folk.research.seats import SeatAssignment
from folk.research.verification import score_source
from folk.utils.logging import get_logger

log = get_logger()

ANCHOR = 50.0


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

            cid = f"C_{iso}_{seat.value}_{d.value}"
            claim_text = (
                f"From a {persona.title.lower()} perspective ({', '.join(persona.focus)}), "
                f"{pack.country}'s {d.label} sits near {proposed:.0f} "
                f"({d.low_pole}<->{d.high_pole}).")
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

            # A counter-claim (confirmation-bias guard): note the opposing pull.
            counter_id = f"CC_{iso}_{seat.value}_{d.value}"
            counter_dir = "supports_low" if direction == "supports_high" else "supports_high"
            claims.append(EvidenceClaim(
                claim_id=counter_id, source_id=sid,
                claim=(f"Counter-consideration: some {persona.focus[0]} evidence pulls "
                       f"{d.label} the other way; weighed but not decisive."),
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

        queries = [f"{pack.country} {d.label} {persona.focus[0]}" for d in DIMENSIONS]
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
        system = persona.system_prompt
        user = self._build_prompt(persona, pack, extra_lenses)
        try:
            payload = self._research_payload(system, user)
        except ResearchCapabilityError:
            raise
        except Exception as exc:  # noqa: BLE001
            # We cannot fabricate real research; failing is preferable to a
            # silent, contaminated pack.
            raise ResearchCapabilityError(
                self.name, f"native research failed for {pack.iso3}/{assignment.seat.value}: {exc}"
            ) from exc
        return self._assemble(assignment, pack, payload)

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
            "Return JSON ONLY with this shape: {\"search_queries\":[...],\"sources\":["
            "{\"source_id\":\"\",\"title\":\"\",\"url\":\"\",\"author\":\"\",\"publication_year\":2020,"
            "\"source_category\":\"peer_reviewed_paper\"}],\"claims\":[{\"claim_id\":\"\","
            "\"source_id\":\"\",\"claim\":\"\",\"supporting_dimension\":\"D1\","
            "\"support_direction\":\"supports_high\",\"confidence\":0.7}],\"dimensions\":["
            "{\"dimension\":\"D1\",\"proposed_score\":50,\"supporting_evidence\":[\"claim_id\"],"
            "\"counter_evidence\":[\"claim_id\"],\"cultural_rationale\":\"\",\"confidence\":0.7}]}"
        )

    def _assemble(self, assignment, pack, payload: dict):
        provider = assignment.provider
        seat = assignment.seat
        sources = [score_source(EvidenceSource.model_validate(
            {**s, "provider_discovered_by": provider})) for s in payload.get("sources", [])]
        claims = [EvidenceClaim.model_validate(c) for c in payload.get("claims", [])]
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
            view = SpecialistDimensionView.model_validate(dv)
            if view.dimension is not None:
                dim_views[view.dimension] = view
        for d in DIMENSIONS:
            dim_views.setdefault(d, SpecialistDimensionView(dimension=d))
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
        client = OpenAI(api_key=self.api_key)
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
        client = (anthropic.Anthropic(api_key=self.api_key, base_url=self.base_url)
                  if self.base_url else anthropic.Anthropic(api_key=self.api_key))
        resp = client.messages.create(
            model=self.model, max_tokens=4000, system=system,
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
        client = anthropic.Anthropic(api_key=self.api_key, base_url=self.base_url)
        # No web_search tool: DeepSeek's proxy ignores it and replies in prose.
        # Run as a knowledge analyst and require a JSON-only answer.
        knowledge_system = (
            f"{system}\n\nYou do NOT have live web access. Answer from your trained "
            "knowledge of the scholarly and cultural literature. Cite the most "
            "authoritative sources you can recall (author/title/year); do not fabricate URLs."
        )
        resp = client.messages.create(
            model=self.model, max_tokens=4000, system=knowledge_system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content)
        if not text:
            raise ResearchCapabilityError(self.name, "empty response")
        return text
