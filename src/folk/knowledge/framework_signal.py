"""Framework Signal Analyzer (Layer 2 core).

Converts a country's raw framework values into a FrameworkSignal per dimension -
the 'common signal beneath five frameworks'. This is the primary evidence object
fed to the council. Encodes the authoritative overrides via the YAML map
(GLOBE Performance Orientation -> D4, GLOBE Uncertainty Avoidance -> D1).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from folk.config import get_settings
from folk.data.framework_map import FRAMEWORK_COLUMNS
from folk.data.loader import DatasetStats
from folk.models.country import FrameworkScores
from folk.models.enums import DIMENSIONS, Dimension, Framework, Polarity
from folk.models.knowledge import FrameworkSignal

_COL_FRAMEWORK = {c: fw for fw, cols in FRAMEWORK_COLUMNS.items() for c in cols}


@dataclass
class ColumnMapping:
    column: str
    dimension: Dimension
    polarity: Polarity
    weight: float
    override: bool = False


@lru_cache
def load_signal_map(path_str: str | None = None) -> dict[Dimension, list[ColumnMapping]]:
    path = Path(path_str) if path_str else get_settings().framework_signal_map_path
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    by_dim: dict[Dimension, list[ColumnMapping]] = {d: [] for d in DIMENSIONS}
    for column, entries in cfg["mappings"].items():
        for e in entries:
            dim = Dimension(e["dimension"])
            by_dim[dim].append(
                ColumnMapping(
                    column=column,
                    dimension=dim,
                    polarity=Polarity(e["polarity"]),
                    weight=float(e["weight"]),
                    override=bool(e.get("override", False)),
                )
            )
    return by_dim


@lru_cache
def dimension_anchor_strength(path_str: str | None = None) -> dict[Dimension, float]:
    path = Path(path_str) if path_str else get_settings().framework_signal_map_path
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    das = cfg.get("dimension_anchor_strength", {})
    return {Dimension(k): float(v) for k, v in das.items()}


class FrameworkSignalAnalyzer:
    """Computes FrameworkSignal objects for one country."""

    def __init__(self, stats: DatasetStats, signal_map_path: Path | None = None) -> None:
        self.stats = stats
        self._map = load_signal_map(str(signal_map_path) if signal_map_path else None)

    def analyze(self, scores: FrameworkScores) -> dict[Dimension, FrameworkSignal]:
        return {dim: self._signal_for(dim, scores) for dim in DIMENSIONS}

    # ------------------------------------------------------------------ #
    def _signal_for(self, dim: Dimension, scores: FrameworkScores) -> FrameworkSignal:
        all_values = scores.all_values()
        # framework -> list of (contribution_toward_high_pole [0-1], weight)
        per_fw: dict[Framework, list[tuple[float, float]]] = {}
        contributing_cols: list[str] = []

        for m in self._map[dim]:
            raw = all_values.get(m.column)
            if raw is None:
                continue
            norm = self.stats.normalise(m.column, raw)
            if norm is None:
                continue
            contribution = norm if m.polarity == Polarity.DIRECT else (1.0 - norm)
            fw = _COL_FRAMEWORK[m.column]
            per_fw.setdefault(fw, []).append((contribution, m.weight))
            contributing_cols.append(m.column)

        if not per_fw:
            return FrameworkSignal(dimension=dim)

        # Aggregate each framework to a single weighted contribution.
        fw_positions: dict[Framework, float] = {}
        fw_weights: dict[Framework, float] = {}
        for fw, pairs in per_fw.items():
            wsum = sum(w for _, w in pairs) or 1.0
            fw_positions[fw] = sum(c * w for c, w in pairs) / wsum
            fw_weights[fw] = wsum

        total_w = sum(fw_weights.values()) or 1.0
        consensus_pos = sum(fw_positions[fw] * fw_weights[fw] for fw in fw_positions) / total_w

        # Agreement: 1 - dispersion of framework positions (weighted by count).
        positions = list(fw_positions.values())
        if len(positions) >= 2:
            stdev = statistics.pstdev(positions)
            agreement = max(0.0, 1.0 - 2.0 * stdev)
        else:
            agreement = 0.6  # single framework: moderate, undisputed but thin
        conflict = round(1.0 - agreement, 4) if len(positions) >= 2 else 0.0

        # Decisiveness: distance of consensus from the midpoint.
        decisiveness = min(1.0, 2.0 * abs(consensus_pos - 0.5))
        n_fw = len(positions)
        coverage_factor = min(1.0, n_fw / 3.0)
        signal_strength = round(
            0.4 * coverage_factor + 0.3 * agreement + 0.3 * decisiveness, 4
        )

        high_side = consensus_pos >= 0.5
        supporting, conflicting = [], []
        for fw, pos in fw_positions.items():
            if abs(pos - 0.5) < 0.05:
                continue  # neutral
            (supporting if (pos >= 0.5) == high_side else conflicting).append(fw.value)

        return FrameworkSignal(
            dimension=dim,
            signal_strength=signal_strength,
            agreement_score=round(agreement, 4),
            conflict_score=conflict,
            consensus=round(consensus_pos * 100.0, 2),
            supporting_frameworks=sorted(supporting),
            conflicting_frameworks=sorted(conflicting),
            contributing_columns=contributing_cols,
        )
