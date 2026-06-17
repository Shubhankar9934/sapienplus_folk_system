"""Layer 2 - Framework Signal Analyzer + Knowledge Builder."""

from __future__ import annotations

import pytest

from folk.data.loader import ExcelLoader
from folk.knowledge.builder import KnowledgeBuilder
from folk.knowledge.framework_signal import FrameworkSignalAnalyzer, dimension_anchor_strength
from folk.knowledge.regions import region_of, regional_neighbours
from folk.models.enums import DIMENSIONS, Dimension


@pytest.fixture(scope="module")
def loaded():
    loader = ExcelLoader()
    base = loader.load_base()
    return loader, {r.iso3: r for r in base}


def test_regions_cover_all_base(loaded):
    _, by_iso = loaded
    missing = [iso for iso in by_iso if region_of(iso) is None]
    assert missing == [], f"Unmapped ISO3s: {missing}"


def test_anchor_strength_loaded():
    das = dimension_anchor_strength()
    assert das[Dimension.D1] == 1.0
    assert das[Dimension.D3] == 0.8


def test_signal_analyzer_produces_all_dims(loaded):
    loader, by_iso = loaded
    analyzer = FrameworkSignalAnalyzer(loader.stats)
    deu = by_iso["DEU"]
    signals = analyzer.analyze(deu.framework_scores)
    assert set(signals.keys()) == set(DIMENSIONS)
    # Germany has full data; D1 signal should be meaningfully strong.
    assert signals[Dimension.D1].signal_strength > 0.0
    assert 0.0 <= signals[Dimension.D1].agreement_score <= 1.0


def test_globe_performance_orientation_feeds_d4_not_d2(loaded):
    loader, by_iso = loaded
    analyzer = FrameworkSignalAnalyzer(loader.stats)
    # Find a country with GLOBE performance orientation present.
    target = next(
        r for r in by_iso.values()
        if r.framework_scores.globe.get("globe_performance_orientation") is not None
    )
    signals = analyzer.analyze(target.framework_scores)
    assert "globe_performance_orientation" in signals[Dimension.D4].contributing_columns
    assert "globe_performance_orientation" not in signals[Dimension.D2].contributing_columns


def test_knowledge_pack_build(loaded):
    loader, by_iso = loaded
    builder = KnowledgeBuilder(loader.stats)
    # Provide a couple of scored neighbours for Germany (baseline vectors).
    scored = {}
    for iso in regional_neighbours("DEU"):
        r = by_iso.get(iso)
        if r is None:
            continue
        scored[iso] = {
            "country": r.country,
            "d1": r.baseline(Dimension.D1), "d2": r.baseline(Dimension.D2),
            "d3": r.baseline(Dimension.D3), "d4": r.baseline(Dimension.D4),
        }
    pack = builder.build(by_iso["DEU"], scored_vectors=scored)
    assert pack.iso3 == "DEU"
    assert pack.region == "Western Europe"
    assert len(pack.framework_signals) == 4
    assert len(pack.anchor_comparisons) == 4  # KOR d1, TUR d2, TUR d4, COL d3
    assert pack.neighbours  # at least one scored neighbour
    assert pack.regional_context.n_in_region >= 1
