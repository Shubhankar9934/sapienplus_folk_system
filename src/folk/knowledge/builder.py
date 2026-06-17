"""Knowledge Builder (Layer 2): assemble the CountryKnowledgePack."""

from __future__ import annotations

import math

from folk.anchors import anchor_locks
from folk.data.loader import DatasetStats
from folk.knowledge.framework_signal import FrameworkSignalAnalyzer
from folk.knowledge.regions import region_of, regional_neighbours
from folk.models.country import ConfidenceInterval, CountryRecord
from folk.models.enums import DIMENSIONS, Dimension
from folk.models.knowledge import (
    AnchorComparison,
    CountryKnowledgePack,
    NeighbourScore,
    RegionalContext,
    UncertaintyFactor,
)

MIDPOINT_LO, MIDPOINT_HI = 40.0, 60.0
WIDE_CI = 25.0
MAX_NEIGHBOURS = 5

ScoreVector = dict[str, float]  # {"country","d1","d2","d3","d4"}


class KnowledgeBuilder:
    def __init__(self, stats: DatasetStats, signal_map_path=None) -> None:
        self.analyzer = FrameworkSignalAnalyzer(stats, signal_map_path=signal_map_path)
        self._anchors = anchor_locks()

    def build(
        self,
        record: CountryRecord,
        scored_vectors: dict[str, ScoreVector] | None = None,
    ) -> CountryKnowledgePack:
        scored_vectors = scored_vectors or {}
        signals = self.analyzer.analyze(record.framework_scores)
        region = record.region or region_of(record.iso3)

        cis = {
            d: record.baselines[d].ci
            for d in DIMENSIONS
            if d in record.baselines and record.baselines[d].ci is not None
        }

        pack = CountryKnowledgePack(
            iso3=record.iso3,
            country=record.country,
            region=region,
            data_status=record.data_status.value,
            record_type=record.record_type.value,
            baselines=dict(record.baselines),
            confidence_intervals={d: cis[d] for d in cis},  # type: ignore[misc]
            framework_signals=signals,
            framework_coverage=[fw.value for fw in record.framework_scores.available_frameworks()],
            framework_conflicts=self._conflicts(signals),
            anchor_comparisons=self._anchor_comparisons(record),
            neighbours=self._neighbours(record, region, scored_vectors),
            regional_context=self._regional_context(record, region, scored_vectors),
            uncertainty_factors=self._uncertainty(record, signals, cis),
        )
        return pack

    # ------------------------------------------------------------------ #
    def _conflicts(self, signals) -> list[str]:
        out = []
        for dim, sig in signals.items():
            if sig.conflicting_frameworks:
                out.append(
                    f"{dim.value}: {', '.join(sig.supporting_frameworks)} vs "
                    f"{', '.join(sig.conflicting_frameworks)} (conflict={sig.conflict_score})"
                )
        return out

    def _anchor_comparisons(self, record: CountryRecord) -> list[AnchorComparison]:
        out = []
        for lock in self._anchors:
            baseline = record.baseline(lock.dimension)
            delta = None if baseline is None else round(baseline - lock.score, 2)
            direction = None
            if delta is not None:
                direction = "Above" if delta > 0 else ("Below" if delta < 0 else "Equal")
            out.append(
                AnchorComparison(
                    anchor_iso3=lock.iso3,
                    anchor_country=lock.country,
                    dimension=lock.dimension,
                    anchor_score=lock.score,
                    baseline_delta=delta,
                    direction=direction,
                )
            )
        return out

    def _neighbours(self, record, region, scored_vectors) -> list[NeighbourScore]:
        candidates = regional_neighbours(record.iso3)
        scored = [(iso, scored_vectors[iso]) for iso in candidates if iso in scored_vectors]

        own = {d.field: record.baseline(d) for d in DIMENSIONS}

        def dist(vec: ScoreVector) -> float:
            total, n = 0.0, 0
            for d in DIMENSIONS:
                a, b = own.get(d.field), vec.get(d.field)
                if a is not None and b is not None:
                    total += (a - b) ** 2
                    n += 1
            return math.sqrt(total) if n else float("inf")

        scored.sort(key=lambda kv: dist(kv[1]))
        out = []
        for iso, vec in scored[:MAX_NEIGHBOURS]:
            out.append(
                NeighbourScore(
                    iso3=iso,
                    country=vec.get("country", iso),
                    d1=vec.get("d1"), d2=vec.get("d2"), d3=vec.get("d3"), d4=vec.get("d4"),
                    relation="regional",
                )
            )
        return out

    def _regional_context(self, record, region, scored_vectors) -> RegionalContext:
        if region is None:
            return RegionalContext()
        members = [scored_vectors[i] for i in regional_neighbours(record.iso3) if i in scored_vectors]
        if not members:
            return RegionalContext(region=region, n_in_region=0)

        means = {}
        for d in DIMENSIONS:
            vals = [m[d.field] for m in members if m.get(d.field) is not None]
            means[d.field] = round(sum(vals) / len(vals), 2) if vals else None

        spreads = []
        for d in DIMENSIONS:
            vals = [m[d.field] for m in members if m.get(d.field) is not None]
            if len(vals) >= 2:
                spreads.append(max(vals) - min(vals))
        spread = round(sum(spreads) / len(spreads), 2) if spreads else None

        return RegionalContext(
            region=region,
            n_in_region=len(members),
            mean_d1=means["d1"], mean_d2=means["d2"], mean_d3=means["d3"], mean_d4=means["d4"],
            spread=spread,
        )

    def _uncertainty(self, record, signals, cis) -> list[UncertaintyFactor]:
        factors: list[UncertaintyFactor] = []
        n_fw = record.framework_scores.n_frameworks
        if n_fw <= 1:
            factors.append(UncertaintyFactor(
                factor=f"Very low framework coverage ({n_fw})", severity=0.9))
        elif n_fw <= 3:
            factors.append(UncertaintyFactor(
                factor=f"Partial framework coverage ({n_fw})", severity=0.5))

        for d in DIMENSIONS:
            ci: ConfidenceInterval | None = cis.get(d)
            if ci is not None and ci.width > WIDE_CI:
                factors.append(UncertaintyFactor(
                    dimension=d, factor=f"Wide CI ({ci.width:.1f})",
                    severity=min(1.0, ci.width / 50.0)))
            baseline = record.baseline(d)
            if baseline is not None and MIDPOINT_LO <= baseline <= MIDPOINT_HI:
                factors.append(UncertaintyFactor(
                    dimension=d, factor="Baseline in 40-60 midpoint band", severity=0.4))
            sig = signals.get(d)
            if sig and sig.signal_strength < 0.4:
                factors.append(UncertaintyFactor(
                    dimension=d, factor=f"Weak framework signal ({sig.signal_strength})",
                    severity=0.5))
        return factors
