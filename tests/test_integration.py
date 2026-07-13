"""Integration smoke test: end-to-end pipeline + exports over a small subset (mock)."""

from __future__ import annotations

import json

import pytest

from folk.export.exporter import Exporter
from folk.llm.factory import ProviderFactory
from folk.models.enums import DIMENSIONS, Dimension
from folk.pipeline.pipeline import Pipeline, processing_order
from folk.storage.db import Database
from folk.storage.repositories import Repositories


@pytest.fixture()
def pipeline(tmp_path):
    db = Database(url=f"sqlite:///{(tmp_path / 'it.sqlite').as_posix()}")
    repos = Repositories(db=db)
    # Per-country checkpoint docs go to the temp dir, never the real outputs/.
    pl = Pipeline(repos=repos, factory=ProviderFactory(), outputs_dir=tmp_path / "out")
    return pl, tmp_path


def test_processing_order_anchors_first(pipeline):
    pl, _ = pipeline
    ordered = processing_order(pl.records)
    first_three = {r.iso3 for r in ordered[:3]}
    assert first_three == {"KOR", "TUR", "COL"}
    assert ordered[-1].record_type.value == "EXTENSION"


def test_end_to_end_subset_and_exports(pipeline):
    pl, tmp_path = pipeline
    # Anchors + a few full-data + one extension country.
    report = pl.run(isos=["KOR", "TUR", "COL", "DEU", "FRA", "JPN", "BHR"], resume=False)

    assert report.total_countries == 7
    assert report.base_countries == 6
    assert report.extension_countries == 1
    assert report.global_calibration is not None
    assert report.run_metrics.calls > 0

    # Anchors locked
    kor = pl.repos.profiles.get("KOR")
    tur = pl.repos.profiles.get("TUR")
    col = pl.repos.profiles.get("COL")
    assert kor.final_scores[Dimension.D1].score == 50
    assert tur.final_scores[Dimension.D2].score == 50
    assert tur.final_scores[Dimension.D4].score == 50
    assert col.final_scores[Dimension.D3].score == 50

    # Extension country has constructed CI + capped confidence
    bhr = pl.repos.profiles.get("BHR")
    assert bhr.record_type.value == "EXTENSION"
    assert bhr.constructed_ci
    assert all(bhr.final_scores[d].confidence.value != "HIGH" for d in DIMENSIONS)

    # Every profile fully scored within 3-97 and has a culture-first profile.
    for p in pl.repos.profiles.all():
        for d in DIMENSIONS:
            assert 3 <= p.final_scores[d].score <= 97
        assert p.cultural_profile is not None
        assert p.audit_trace is not None
        # Canonical-score invariant: every audit record agrees with final_scores.
        for a in p.adjustment_log:
            assert a.baseline == p.baseline_scores[a.dimension]
            assert int(round(a.final)) == p.final_scores[a.dimension].score
        for dr in p.dissent_record:
            assert int(round(dr.final_score)) == p.final_scores[dr.dimension].score
        # The Cultural Fingerprint snapshot mirrors the final scores.
        snap = {s.dimension: s.score for s in p.cultural_profile.snapshot}
        for d in DIMENSIONS:
            assert snap[d] == p.final_scores[d].score

        cp = p.cultural_profile
        from folk.cultural.engine import CulturalProfileEngine
        banned_titles = {"identity & belonging", "everyday expression",
                         "order & structure", "ambition & drive"}
        for theme in cp.cultural_themes:
            # Themes must be dynamically named, not the renamed dimensions.
            assert theme.title.lower() not in banned_titles
            # Theme names are never pure dimension restatements.
            assert not CulturalProfileEngine._is_dimension_restatement(theme.title)
            # Confidence is now a transparent three-part breakdown.
            c = theme.confidence
            assert 0 <= c.evidence_strength <= 100
            assert 0 <= c.expert_agreement <= 100
            assert 0 <= c.framework_agreement <= 100
            # Every kept theme has a deterministic confidence narrative.
            assert c.confidence_explanation
            assert c.confidence_explanation.endswith(".")
        # No template restatements leak into observations.
        all_texts = [o.text for t in cp.cultural_themes for o in t.observations]
        all_texts += [d.text for d in cp.historical_drivers]
        for text in all_texts:
            assert "sits near" not in text.lower()
            assert "counter-consideration" not in text.lower()
        # good_for is populated and is not the old generic catch-all row.
        assert cp.good_for
        # Lived-experience layer is populated (mock research tags every domain).
        assert not cp.lived_experience.is_empty()

        # Confidence labels are computed for every theme (Contested..Very High).
        bands = {"Contested", "Low", "Moderate", "High", "Very High"}
        for theme in cp.cultural_themes:
            assert theme.confidence.evidence_strength_label in bands
            assert theme.confidence.expert_agreement_label in bands
            assert theme.confidence.framework_agreement_label in bands

        # Every new human-experience item is grounded: each cited claim_id
        # resolves to a real claim the specialists discovered.
        valid_claims = {c.claim_id for pk in p.specialist_evidence_packs for c in pk.claims}
        must_be_grounded = (
            list(cp.competing_forces) + list(cp.newcomer_first_impressions)
            + list(cp.success_factors) + list(cp.failure_factors)
            + list(cp.communication_decoder) + list(cp.culture_in_transition)
        )
        for facet_name in type(cp.friendship_map).FIELDS:
            facet = getattr(cp.friendship_map, facet_name)
            if facet.label:
                must_be_grounded.append(facet)
        if cp.cultural_archetype.title:
            must_be_grounded.append(cp.cultural_archetype)
        for item in must_be_grounded:
            assert item.claim_ids, f"{p.iso3}: ungrounded item {item}"
            assert all(cid in valid_claims for cid in item.claim_ids)
        # Contradictions carry both poles + an explanation.
        for force in cp.competing_forces:
            assert force.pulls_toward and force.but_also
        # Similar-culture explanations, when present, are grounded too.
        for sc in cp.similar_cultures:
            if sc.explanation:
                assert all(cid in valid_claims for cid in sc.claim_ids)

        # Every Cultural Fingerprint row carries a non-empty explanation
        # (grounded take or reading fallback).
        for row in cp.snapshot:
            assert row.explanation

        # Culture-at-a-glance: deterministic, 4-6 one-sentence bullets when
        # present (hidden when there is not enough strong material).
        glance = cp.culture_at_a_glance
        assert len(glance) == 0 or 4 <= len(glance) <= 6
        for bullet in glance:
            assert bullet and "\n" not in bullet

        # Life-feels-like, when present, is grounded.
        if cp.life_feels_like.text:
            assert cp.life_feels_like.claim_ids
            assert all(cid in valid_claims for cid in cp.life_feels_like.claim_ids)

        # Experience variations: grounded, both groups + a difference.
        for ev in cp.experience_variations:
            assert ev.group_a and ev.group_b and ev.difference
            assert ev.claim_ids
            assert all(cid in valid_claims for cid in ev.claim_ids)

        # Country uniqueness: grounded, title + explanation.
        for facet in cp.country_uniqueness:
            assert facet.title and facet.explanation
            assert facet.claim_ids
            assert all(cid in valid_claims for cid in facet.claim_ids)

        # Multi-source clustering: at least one clustered observation cites 2+
        # distinct sources somewhere in the profile.
        clustered = [o for t in cp.cultural_themes for o in t.observations]
        clustered += list(cp.success_factors) + list(cp.failure_factors)
        for field in type(cp.lived_experience).FIELDS:
            clustered += list(getattr(cp.lived_experience, field))
        assert any(o.sources_count >= 2 for o in clustered), p.iso3

    # Default exports: one self-contained doc per country + a slim index.
    out_dir = tmp_path / "out"
    paths = Exporter(pl.repos, out_dir).export_all(report)
    for path in paths.values():
        assert path.exists()
    country_docs = list((out_dir / "countries").glob("*.json"))
    assert len(country_docs) == 7
    index = json.loads(paths["index_json"].read_text(encoding="utf-8"))
    assert len(index["countries"]) == 7

    # A per-country doc carries the culture-first contract.
    deu = json.loads((out_dir / "countries" / "DEU.json").read_text(encoding="utf-8"))
    deu_cp = deu["cultural_profile"]
    assert deu_cp["snapshot"]
    assert deu_cp["good_for"]
    assert deu_cp["lived_experience"]
    assert any(deu_cp["lived_experience"].get(f) for f in
               ("daily_life", "workplace_norms", "communication_style",
                "friendship_social", "society", "social_mistakes_to_avoid",
                "status_signals"))
    # The new human-experience sections serialise into the per-country doc.
    assert deu_cp["cultural_archetype"]["title"]
    assert deu_cp["newcomer_first_impressions"]
    assert deu_cp["success_factors"]
    assert deu_cp["failure_factors"]
    assert deu_cp["communication_decoder"]
    assert deu_cp["culture_in_transition"]
    assert deu_cp["similar_cultures"]
    # Depth-upgrade sections serialise too.
    assert "culture_at_a_glance" in deu_cp
    assert "life_feels_like" in deu_cp
    assert deu_cp["experience_variations"]
    assert deu_cp["country_uniqueness"]
    # Per-dimension explanations + per-theme confidence narratives are present.
    assert all(row.get("explanation") for row in deu_cp["snapshot"])
    assert all(t["confidence"].get("confidence_explanation")
               for t in deu_cp["cultural_themes"])
    assert any(deu_cp["friendship_map"].get(f, {}).get("label")
               for f in ("making_friends", "friendship_depth", "circle_size",
                         "trust_formation", "work_personal_mixing"))
    # Lived-experience claim_ids resolve into the doc's sources block.
    assert deu["sources"]
    assert "methodology" in deu


def test_confidence_label_bands():
    from folk.models.cultural import ThemeConfidence, confidence_label

    assert confidence_label(None) == "Contested"
    assert confidence_label(0) == "Contested"
    assert confidence_label(29) == "Contested"
    assert confidence_label(30) == "Low"
    assert confidence_label(49) == "Low"
    assert confidence_label(50) == "Moderate"
    assert confidence_label(69) == "Moderate"
    assert confidence_label(70) == "High"
    assert confidence_label(84) == "High"
    assert confidence_label(85) == "Very High"
    assert confidence_label(100) == "Very High"
    # ThemeConfidence derives its labels from the numbers automatically.
    tc = ThemeConfidence(evidence_strength=88, expert_agreement=55, framework_agreement=10)
    assert tc.evidence_strength_label == "Very High"
    assert tc.expert_agreement_label == "Moderate"
    assert tc.framework_agreement_label == "Contested"


def test_theme_name_restatement_validator():
    from folk.cultural.engine import CulturalProfileEngine as E

    # Pure dimension restatements / near-synonyms are rejected.
    for bad in ("Achievement Culture", "Collective Commitment",
                "Emotional Restraint", "Structured Independence",
                "Hierarchy", "Individualism"):
        assert E._is_dimension_restatement(bad), bad
    # Country-specific / memorable names survive (carry a non-banned token).
    for good in ("Nunchi and Social Awareness", "Achievement as Moral Duty",
                 "Reserved Trust", "Rule-Based Society", "Quiet Excellence"):
        assert not E._is_dimension_restatement(good), good


def test_prefer_multi_source_drops_single_when_peer_exists():
    from folk.cultural.engine import CulturalProfileEngine as E
    from folk.models.cultural import Observation

    multi = Observation(text="Clustered insight.", sources_count=3)
    single = Observation(text="Lone fact.", sources_count=1)
    kept = E._prefer_multi_source([single, multi])
    # The multi-source observation sorts first and the single-source one is
    # dropped because a multi-source alternative exists.
    assert kept[0] is multi
    assert single not in kept
    # With only single-source items, nothing is dropped (never returns empty).
    only_single = E._prefer_multi_source([single])
    assert only_single == [single]


def test_resume_skips_processed(pipeline):
    pl, _ = pipeline
    pl.run(isos=["KOR"], resume=False)
    before = pl.run_metrics.calls
    # Resume should skip the already-processed country (no new calls).
    pl.run(isos=["KOR"], resume=True)
    assert pl.run_metrics.calls == before
