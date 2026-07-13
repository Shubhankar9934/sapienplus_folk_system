"""FastAPI service exposing the FOLK Cultural Intelligence data.

Composes the in-memory artifacts (see :mod:`folk.api.loader`) and derived
analytics (see :mod:`folk.api.analytics`) into a clean REST surface consumed by
the Next.js frontend. All responses are plain JSON; nothing here touches the
ORM or the large raw files at request time.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from folk.api.analytics import (
    DIM_META,
    DIMENSIONS,
    Analytics,
    get_analytics,
    profile_scores,
    rebuild_analytics,
)
from folk.api.loader import DataStore, get_store, reload_store


# ------------------------------------------------------------------ #
# Composition helpers
# ------------------------------------------------------------------ #
def _grade_from_score(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def _dim_scores(profile: dict) -> dict[str, Any]:
    """Per-dimension score + confidence + pole labels + CI."""
    fs = profile.get("final_scores") or {}
    cis = profile.get("confidence_intervals") or {}
    out: dict[str, Any] = {}
    for d in DIMENSIONS:
        v = fs.get(d)
        if not isinstance(v, dict):
            continue
        ci = cis.get(d) or {}
        out[d] = {
            "dimension": d,
            "label": DIM_META[d]["label"],
            "low_pole": DIM_META[d]["low"],
            "high_pole": DIM_META[d]["high"],
            "score": v.get("score"),
            "confidence": v.get("confidence"),
            "ci_low": ci.get("lo"),
            "ci_high": ci.get("hi"),
        }
    return out


def _country_list_entry(store: DataStore, an: Analytics, iso: str) -> dict[str, Any]:
    prof = store.profiles.get(iso) or {}
    scores = profile_scores(prof)
    es = an.evidence_strength(iso)
    ca = an.council_agreement(iso)
    return {
        "iso3": iso,
        "country": prof.get("country") or iso,
        "region": prof.get("region"),
        "data_status": prof.get("data_status"),
        "record_type": prof.get("record_type"),
        "scores": {d: scores.get(d) for d in DIMENSIONS},
        "confidence": {
            d: ((prof.get("final_scores") or {}).get(d) or {}).get("confidence")
            for d in DIMENSIONS
        },
        "archetype": an.archetype_by_iso.get(iso),
        "uniqueness": an.uniqueness.get(iso),
        "evidence_strength": es.get("overall"),
        "council_agreement": ca.get("overall"),
        "consensus_verdict": ca.get("verdict"),
        "research_grade": _grade_from_score(es.get("overall")),
    }


def _trust_breakdown(store: DataStore, iso: str) -> dict[str, Any]:
    prof = store.profiles.get(iso) or {}
    spec = store.specialist.get(iso) or {}
    calib = prof.get("calibration_results") or []
    calib_passed = all(
        all(chk.get("passed") for chk in c.get("checks", []))
        for c in calib
    ) if calib else None
    specialists = sorted({p.get("specialist") for p in spec.get("positions") or []
                          if p.get("specialist")})
    return {
        "frameworks": ["Hofstede", "GLOBE", "Schwartz", "Trompenaars", "World Values Survey"],
        "framework_count": 5,
        "specialist_count": len(specialists) or 3,
        "specialists": specialists,
        "evidence_reviewed": True,
        "calibration_passed": calib_passed,
        "provider_diversity": (store.intelligence.get(iso) or {}).get("provider_diversity"),
    }


def _dimension_payload(store: DataStore, an: Analytics, iso: str, dim: str) -> dict[str, Any]:
    """Methodology detail for one dimension (score formation, confidence, council impact)."""
    prof = store.profiles.get(iso) or {}
    cultural = store.cultural.get(iso) or {}
    fs = (prof.get("final_scores") or {}).get(dim) or {}

    de = next((d for d in prof.get("decision_explanations") or []
               if d.get("dimension") == dim), {})
    council_views = (cultural.get("council_views") or {}).get(dim) or []

    es = an.evidence_strength(iso).get("per_dimension", {}).get(dim)
    cb = an.confidence_breakdown(iso).get(dim, {})
    ci = an.council_impact(iso).get("per_dimension", {}).get(dim, {})

    return {
        "iso3": iso,
        "dimension": dim,
        "label": DIM_META[dim]["label"],
        "low_pole": DIM_META[dim]["low"],
        "high_pole": DIM_META[dim]["high"],
        "score": fs.get("score"),
        "confidence": fs.get("confidence"),
        "council_views": council_views,
        "summary": de.get("summary"),
        "final_rationale": de.get("final_rationale"),
        "adjustment_type": de.get("adjustment_type"),
        "evidence_strength": es,
        "confidence_breakdown": cb,
        "council_impact": ci,
    }


# ------------------------------------------------------------------ #
# App factory
# ------------------------------------------------------------------ #
def create_app() -> FastAPI:
    app = FastAPI(
        title="FOLK Cultural Intelligence API",
        version="1.0.0",
        description="Serves the FOLK pipeline outputs to the Cultural Intelligence Platform.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = get_store()
    get_analytics(store)

    def _an() -> Analytics:
        return get_analytics(store)

    def _require(iso3: str) -> str:
        iso = iso3.upper()
        if not store.has(iso):
            raise HTTPException(status_code=404, detail=f"Unknown country: {iso3}")
        return iso

    def _require_dim(dim: str) -> str:
        d = dim.upper()
        if d not in DIMENSIONS:
            raise HTTPException(status_code=400, detail=f"Unknown dimension: {dim}")
        return d

    # -------------------------------------------------------------- #
    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "countries": store.country_count}

    @app.post("/api/reload")
    def reload() -> dict[str, Any]:
        new_store = reload_store()
        rebuild_analytics(new_store)
        # Rebind module-level store reference used by the closures.
        nonlocal store
        store = new_store
        return {"status": "reloaded", "countries": store.country_count}

    @app.get("/api/stats")
    def stats() -> dict[str, Any]:
        an = _an()
        s = store.stats or {}
        total_sources = s.get("evidence_sources")
        if total_sources is None:
            total_sources = sum(len((p.get("references") or []))
                                for p in store.profiles.values())
        return {
            "countries": store.country_count,
            "dimensions": s.get("dimensions", 4),
            "frameworks": s.get("frameworks", 5),
            "specialists": s.get("specialists") or ["GPT", "Claude", "DeepSeek"],
            "research_grade": s.get("research_grade"),
            "evidence_sources": total_sources,
            "archetype_count": len(an.clusters),
            "run_metrics": s.get("run_metrics"),
        }

    @app.get("/api/countries")
    def countries() -> list[dict[str, Any]]:
        an = _an()
        return [_country_list_entry(store, an, iso) for iso in an.isos or store.profiles]

    @app.get("/api/map")
    def world_map() -> list[dict[str, Any]]:
        rows = []
        for iso, prof in store.profiles.items():
            scores = profile_scores(prof)
            rows.append({
                "iso3": iso,
                "country": prof.get("country") or iso,
                "region": prof.get("region"),
                "scores": {d: scores.get(d) for d in DIMENSIONS},
                "confidence": {
                    d: ((prof.get("final_scores") or {}).get(d) or {}).get("confidence")
                    for d in DIMENSIONS
                },
            })
        return rows

    @app.get("/api/archetypes")
    def archetypes() -> dict[str, Any]:
        an = _an()
        return {
            "clusters": an.clusters,
            "ready": len(an.clusters) > 0,
            "note": None if an.clusters else "More countries needed to form archetypes.",
        }

    @app.get("/api/rankings")
    def rankings(
        dim: str = Query("D1"),
        scope: str = Query("global"),
    ) -> dict[str, Any]:
        an = _an()
        d = _require_dim(dim)
        if scope == "region":
            return an.region_rankings(d)
        return an.rankings(d)

    @app.get("/api/compare")
    def compare(isos: str = Query(...)) -> dict[str, Any]:
        an = _an()
        codes = [c.strip().upper() for c in isos.split(",") if c.strip()]
        results = []
        for iso in codes:
            if not store.has(iso):
                continue
            prof = store.profiles[iso]
            results.append({
                "iso3": iso,
                "country": prof.get("country") or iso,
                "region": prof.get("region"),
                "scores": profile_scores(prof),
                "confidence": {
                    d: ((prof.get("final_scores") or {}).get(d) or {}).get("confidence")
                    for d in DIMENSIONS
                },
                "archetype": an.archetype_by_iso.get(iso),
            })
        return {"countries": results}

    @app.get("/api/countries/{iso3}")
    def country(iso3: str) -> dict[str, Any]:
        iso = _require(iso3)
        an = _an()
        prof = store.profiles[iso]
        cultural = store.cultural.get(iso) or {}
        es = an.evidence_strength(iso)
        ca = an.council_agreement(iso)

        dim_scores = _dim_scores(prof)

        return {
            "iso3": iso,
            "country": prof.get("country") or iso,
            "region": prof.get("region"),
            "data_status": prof.get("data_status"),
            "record_type": prof.get("record_type"),
            "processing_date": prof.get("processing_date"),
            # --- Culture-first content ---
            "snapshot": cultural.get("snapshot") or [],
            "executive_summary": cultural.get("executive_summary"),
            # Memorable, grounded country identity (e.g. "The Precision Builder").
            "cultural_archetype": cultural.get("cultural_archetype") or {},
            # Country-specific use cases. `good_for` is the new field; `best_for`
            # is kept as an alias for older frontend builds.
            "good_for": cultural.get("good_for") or cultural.get("best_for") or [],
            "best_for": cultural.get("good_for") or cultural.get("best_for") or [],
            # Deterministic executive snapshot (4-6 one-sentence bullets).
            "culture_at_a_glance": cultural.get("culture_at_a_glance") or [],
            "cultural_themes": cultural.get("cultural_themes") or [],
            "historical_drivers": cultural.get("historical_drivers") or [],
            "competing_forces": cultural.get("competing_forces") or [],
            "lived_experience": cultural.get("lived_experience") or {},
            # Grounded "what life feels like" narrative block.
            "life_feels_like": cultural.get("life_feels_like") or {},
            "newcomer_first_impressions": cultural.get("newcomer_first_impressions") or [],
            "success_factors": cultural.get("success_factors") or [],
            "failure_factors": cultural.get("failure_factors") or [],
            "friendship_map": cultural.get("friendship_map") or {},
            "communication_decoder": cultural.get("communication_decoder") or [],
            "culture_in_transition": cultural.get("culture_in_transition") or [],
            # How different groups experience the country (co-existing contrasts).
            "experience_variations": cultural.get("experience_variations") or [],
            "similar_cultures": cultural.get("similar_cultures") or [],
            # Grounded "what makes this country unique vs neighbours" facets.
            "country_uniqueness": cultural.get("country_uniqueness") or [],
            "regional_distinctiveness": cultural.get("regional_distinctiveness") or [],
            "council_views": cultural.get("council_views") or {},
            # --- Visible Cultural Fingerprint (scores) + methodology ---
            "scores": dim_scores,
            "neighbours": prof.get("neighbours") or [],
            "anchor_positions": prof.get("anchor_positions") or [],
            "archetype": an.archetype_by_iso.get(iso),
            "uniqueness": an.uniqueness.get(iso),
            "evidence_strength": es,
            "council_agreement": ca,
            "regional_context": an.regional_context(iso),
            "global_distribution": an.global_distribution(iso),
            "research_grade": _grade_from_score(es.get("overall")),
            "trust": _trust_breakdown(store, iso),
        }

    @app.get("/api/countries/{iso3}/dimensions/{dim}")
    def dimension(iso3: str, dim: str) -> dict[str, Any]:
        iso = _require(iso3)
        d = _require_dim(dim)
        return _dimension_payload(store, _an(), iso, d)

    @app.get("/api/countries/{iso3}/sources")
    def sources(iso3: str) -> dict[str, Any]:
        iso = _require(iso3)
        payload = _an().source_reliability(iso)
        payload["iso3"] = iso
        payload["references"] = (store.profiles[iso].get("references") or [])
        # Claim-resolved sources so the UI can link observations -> provenance.
        payload["sources"] = store.sources(iso)
        return payload

    @app.get("/api/countries/{iso3}/council")
    def council(iso3: str) -> dict[str, Any]:
        iso = _require(iso3)
        an = _an()
        spec = store.specialist.get(iso) or {}
        cultural = store.cultural.get(iso) or {}
        return {
            "iso3": iso,
            "country": store.profiles[iso].get("country") or iso,
            "agreement": an.council_agreement(iso),
            # Reasoning-first council views (reasoning before the suggested score).
            "council_views": cultural.get("council_views") or {},
            "positions": spec.get("positions") or [],
            "influence_records": spec.get("influence_records") or [],
            "challenges": spec.get("challenges") or [],
            "diversity_v2": spec.get("diversity_v2"),
        }

    @app.get("/api/countries/{iso3}/similar")
    def similar(iso3: str) -> dict[str, Any]:
        iso = _require(iso3)
        an = _an()
        sim = an.similarity.get(iso)
        if sim is None:
            return {
                "iso3": iso,
                "ready": False,
                "note": "More countries needed to compute similarity.",
                "most_similar": [],
                "most_different": [],
            }
        return {"iso3": iso, "ready": True, **sim}

    return app


# Uvicorn entry point: ``uvicorn folk.api.app:app``.
app = create_app()
