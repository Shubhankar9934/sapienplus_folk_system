"""Source verification + provenance/quality scoring.

URL verification is offline-safe: when disabled or unreachable the source is
marked UNVERIFIED/UNREACHABLE and is never treated as authoritative. Quality is
a deterministic function of the source category tier, recency, and verification
status. Low-quality sources are down-weighted but never excluded (Req 3).
"""

from __future__ import annotations

from datetime import datetime, timezone

from folk.config import get_settings
from folk.models.enums import EvidenceVerificationStatus, VerificationStatus
from folk.models.research import EvidenceSource
from folk.utils.logging import get_logger

log = get_logger()

_RECENCY_FULL_YEARS = 15   # within this many years -> no recency penalty
_RECENCY_FLOOR = 0.6       # oldest sources keep at least this fraction

# Providers that perform native web search (their sources are provider-verifiable);
# DeepSeek is a knowledge-only analyst, so its sources stay knowledge-only.
_WEB_SEARCH_PROVIDERS = {"openai", "anthropic"}
_STRONG_PROVENANCE = 0.6   # tier*recency at/above this counts as strong provenance
_PARTIAL_PROVENANCE = 0.4  # some provenance signal


def verify_url(url: str | None, *, timeout: float = 4.0) -> VerificationStatus:
    """Best-effort HEAD/GET check. Returns UNVERIFIED when disabled/offline."""
    settings = get_settings()
    if not url or not getattr(settings, "enable_url_verification", False) or settings.is_mock:
        return VerificationStatus.UNVERIFIED
    if not url.lower().startswith(("http://", "https://")):
        return VerificationStatus.UNREACHABLE
    try:
        import httpx

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.head(url)
            if resp.status_code >= 400:
                resp = client.get(url)
            return (VerificationStatus.VERIFIED if resp.status_code < 400
                    else VerificationStatus.UNREACHABLE)
    except Exception as exc:  # noqa: BLE001 - network failures are non-fatal
        log.warning(f"URL verification failed for {url}: {exc}")
        return VerificationStatus.UNREACHABLE


def _recency_factor(year: int | None) -> float:
    if not year:
        return 0.85
    age = datetime.now(timezone.utc).year - int(year)
    if age <= _RECENCY_FULL_YEARS:
        return 1.0
    # Linear decay down to the floor over the following 50 years.
    decayed = 1.0 - (age - _RECENCY_FULL_YEARS) / 50.0
    return round(max(_RECENCY_FLOOR, decayed), 3)


def _verification_factor(status: VerificationStatus) -> float:
    return {
        VerificationStatus.VERIFIED: 1.0,
        VerificationStatus.UNVERIFIED: 0.85,
        VerificationStatus.UNREACHABLE: 0.6,
    }[status]


def score_source(source: EvidenceSource, *, verify: bool = True) -> EvidenceSource:
    """Set verification_status (optionally live) and source_quality in place,
    plus the evidence-grade verification layer (Req 6): a 3-state status, a
    human-readable reason, the method used, and a 0-1 verification score."""
    if verify:
        source.verification_status = verify_url(source.url)
    base = source.source_category.quality_tier
    recency = _recency_factor(source.publication_year)
    provenance = base * recency
    quality = provenance * _verification_factor(source.verification_status)
    source.source_quality = round(max(0.05, min(1.0, quality)), 4)
    _apply_evidence_verification(source, provenance=provenance, verify=verify)
    return source


def _apply_evidence_verification(source: EvidenceSource, *, provenance: float,
                                 verify: bool) -> None:
    """Derive the richer evidence-verification grade from URL reachability,
    provenance tier, recency, and how the source was discovered."""
    settings = get_settings()
    url_status = source.verification_status
    reachable = url_status == VerificationStatus.VERIFIED
    strong = provenance >= _STRONG_PROVENANCE
    partial = provenance >= _PARTIAL_PROVENANCE

    # Method: a real URL probe takes precedence; otherwise it is provider-native
    # (web-search providers) or knowledge-only (DeepSeek / offline / mock).
    url_checked = (verify and bool(source.url)
                   and getattr(settings, "enable_url_verification", False)
                   and not settings.is_mock
                   and str(source.url).lower().startswith(("http://", "https://")))
    provider = (source.provider_discovered_by or "").lower()
    if url_checked:
        method = "url_check"
    elif provider in _WEB_SEARCH_PROVIDERS:
        method = "provider_native"
    else:
        method = "knowledge_only"
    source.verification_method = method

    if reachable and strong:
        status = EvidenceVerificationStatus.VERIFIED
        reason = "URL reachable and high-provenance source."
    elif reachable or strong:
        status = EvidenceVerificationStatus.PARTIALLY_VERIFIED
        reason = ("URL reachable but provenance is moderate." if reachable
                  else "Strong provenance but URL not confirmed reachable.")
    elif url_status == VerificationStatus.UNVERIFIED and partial:
        status = EvidenceVerificationStatus.PARTIALLY_VERIFIED
        reason = "URL not checked (offline/native); moderate provenance only."
    else:
        status = EvidenceVerificationStatus.UNVERIFIED
        reason = "Neither reachable nor strongly provenanced."
    source.evidence_verification = status
    source.verification_reason = reason

    reach_factor = _verification_factor(url_status)
    source.verification_score = round(max(0.0, min(1.0, 0.5 * reach_factor + 0.5 * provenance)), 4)
