"""Layer 3 - Evidence Engine."""

from __future__ import annotations

import pytest

from folk.data.loader import ExcelLoader
from folk.evidence.engine import EvidenceEngine
from folk.knowledge.builder import KnowledgeBuilder
from folk.knowledge.regions import regional_neighbours
from folk.models.enums import DIMENSIONS, Dimension, EvidenceCategory


@pytest.fixture(scope="module")
def germany_pack():
    loader = ExcelLoader()
    by_iso = {r.iso3: r for r in loader.load_base()}
    builder = KnowledgeBuilder(loader.stats)
    scored = {}
    for iso in regional_neighbours("DEU"):
        r = by_iso.get(iso)
        if r:
            scored[iso] = {"country": r.country, "d1": r.baseline(Dimension.D1),
                           "d2": r.baseline(Dimension.D2), "d3": r.baseline(Dimension.D3),
                           "d4": r.baseline(Dimension.D4)}
    return builder.build(by_iso["DEU"], scored_vectors=scored)


def test_evidence_for_all_dimensions(germany_pack):
    ev = EvidenceEngine().build(germany_pack)
    assert set(ev.keys()) == set(DIMENSIONS)
    for dim in DIMENSIONS:
        assert ev[dim].items, f"no evidence for {dim}"


def test_evidence_has_quantitative_and_anchor(germany_pack):
    ev = EvidenceEngine().build(germany_pack)
    d1 = ev[Dimension.D1]
    cats = {i.category for i in d1.items}
    assert EvidenceCategory.QUANTITATIVE in cats
    assert EvidenceCategory.ANCHOR_RELATIVE in cats


def test_evidence_ids_unique(germany_pack):
    ev = EvidenceEngine().build(germany_pack)
    ids = [i.evidence_id for de in ev.values() for i in de.items]
    assert len(ids) == len(set(ids))


def test_sparse_country_gets_qualitative_flag():
    loader = ExcelLoader()
    by_iso = {r.iso3: r for r in loader.load_base()}
    # Afghanistan has a single framework -> qualitative flag expected.
    builder = KnowledgeBuilder(loader.stats)
    pack = builder.build(by_iso["AFG"])
    ev = EvidenceEngine().build(pack)
    cats = {i.category for de in ev.values() for i in de.items}
    assert EvidenceCategory.QUALITATIVE in cats
