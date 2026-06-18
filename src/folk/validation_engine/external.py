"""Objective 4 - External Validation Engine.

Measures whether FOLK scores align with established cultural datasets by
correlating each FOLK dimension against the relevant raw framework column(s)
across all base countries. Reports Pearson, Spearman, and a rank-agreement
fraction per comparison plus aggregate external-validity indicators.

Uses ``scipy.stats`` when available, otherwise a NumPy fallback. WVS axes
(Traditional/Secular, Self-Expression) are not present verbatim in the dataset,
so composite proxies are used and explicitly flagged as approximate.
"""

from __future__ import annotations

import numpy as np

from folk.models.country import CountryRecord
from folk.models.enums import DIMENSIONS, Dimension
from folk.models.external import (
    CorrelationResult,
    ExternalValidationReport,
    ExternalValidationV2,
)
from folk.models.profile import CountryProfile
from folk.utils.logging import get_logger

try:  # optional dependency
    from scipy import stats as _scipy_stats
except Exception:  # noqa: BLE001
    _scipy_stats = None

log = get_logger()


# (folk_dim, dataset, label, [columns], approximate, note)
_COMPARISONS: list[tuple[Dimension, str, str, list[str], bool, str]] = [
    (Dimension.D1, "hofstede", "hofstede_individualism", ["hofstede_individualism"], False,
     "FOLK Identity (Self) vs Hofstede Individualism"),
    (Dimension.D3, "hofstede", "hofstede_uncertainty_avoidance", ["hofstede_uncertainty_avoidance"],
     False, "FOLK Structure (Certain) vs Hofstede Uncertainty Avoidance"),
    (Dimension.D4, "hofstede", "hofstede_masculinity", ["hofstede_masculinity"], False,
     "FOLK Drive (Striving) vs Hofstede Masculinity"),
    (Dimension.D4, "globe", "globe_performance_orientation", ["globe_performance_orientation"],
     False, "FOLK Drive vs GLOBE Performance Orientation"),
    (Dimension.D1, "globe", "globe_institutional_collectivism", ["globe_institutional_collectivism"],
     False, "FOLK Identity vs GLOBE Institutional Collectivism (collectivism is the low pole)"),
    (Dimension.D1, "wvs", "wvs_traditional_secular(proxy)",
     ["wvs_defiance", "wvs_disbelief", "wvs_scepticism", "wvs_relativism"], True,
     "FOLK Identity vs WVS Traditional/Secular proxy (defiance/disbelief/scepticism/relativism)"),
    (Dimension.D2, "wvs", "wvs_self_expression(proxy)",
     ["wvs_autonomy", "wvs_choice", "wvs_voice", "wvs_equality"], True,
     "FOLK Expression vs WVS Self-Expression proxy (autonomy/choice/voice/equality)"),
    # ---- Schwartz (Req 5) ----
    (Dimension.D1, "schwartz", "schwartz_autonomy(proxy)",
     ["schwartz_affective_autonomy", "schwartz_intellectual_autonomy", "schwartz_egalitarianism"],
     True, "FOLK Identity (Self) vs Schwartz Autonomy/Egalitarianism proxy"),
    (Dimension.D4, "schwartz", "schwartz_mastery", ["schwartz_mastery"], False,
     "FOLK Drive (Striving) vs Schwartz Mastery"),
    (Dimension.D3, "schwartz", "schwartz_harmony(inverse)", ["schwartz_harmony"], True,
     "FOLK Structure (Certain) vs Schwartz Harmony (harmony loads the Fluid pole; expect negative)"),
]


class ExternalValidationEngine:
    def validate(
        self, profiles: list[CountryProfile], records: list[CountryRecord]
    ) -> ExternalValidationReport:
        final_by_iso = {
            p.iso3: {d: p.final_scores[d].score for d in DIMENSIONS if d in p.final_scores}
            for p in profiles if p.record_type.value == "BASE"
        }
        values_by_iso = {r.iso3: r.framework_scores.all_values() for r in records}
        return self.validate_scores(final_by_iso, values_by_iso)

    def validate_scores(
        self,
        final_by_iso: dict[str, dict[Dimension, float]],
        values_by_iso: dict[str, dict[str, float | None]],
    ) -> ExternalValidationReport:
        comparisons: list[CorrelationResult] = []
        coverage: dict[str, int] = {}
        for dim, dataset, label, cols, approx, note in _COMPARISONS:
            folk_vals: list[float] = []
            ext_vals: list[float] = []
            for iso, scores in final_by_iso.items():
                if dim not in scores:
                    continue
                ext = self._composite(values_by_iso.get(iso, {}), cols)
                if ext is None:
                    continue
                folk_vals.append(float(scores[dim]))
                ext_vals.append(ext)
            n = len(folk_vals)
            coverage[dataset] = max(coverage.get(dataset, 0), n)
            pearson, spearman, rank_agree = self._correlate(folk_vals, ext_vals)
            comparisons.append(CorrelationResult(
                folk_dimension=dim.value, dataset=dataset, external_measure=label, n=n,
                pearson=pearson, spearman=spearman, rank_agreement=rank_agree,
                approximate=approx, note=note,
            ))

        report = ExternalValidationReport(comparisons=comparisons, coverage=coverage)
        self._aggregate(report)
        if not _scipy_stats:
            report.notes.append("scipy not installed; used NumPy fallback for correlations.")
        report.notes.append(
            "WVS/Schwartz proxy axes are composed from available columns; treat as approximate.")
        return report

    # ------------------------------------------------------------------ #
    def validate_v2(
        self, profiles: list[CountryProfile], records: list[CountryRecord]
    ) -> ExternalValidationV2:
        """Req 5 - external validation across Hofstede, GLOBE, WVS, and Schwartz.

        Reuses the same Pearson/Spearman/rank-agreement comparisons and adds a
        per-dataset breakdown plus an ``available`` flag for the dashboard."""
        base = self.validate(profiles, records)
        datasets = sorted({c.dataset for c in base.comparisons})
        per_dataset: dict[str, float | None] = {}
        for ds in datasets:
            prs = [abs(c.pearson) for c in base.comparisons
                   if c.dataset == ds and c.pearson is not None]
            per_dataset[ds] = round(sum(prs) / len(prs), 4) if prs else None
        available = any(c.pearson is not None for c in base.comparisons)
        notes = list(base.notes)
        notes.append(f"Datasets covered: {', '.join(datasets) or 'none'}.")
        return ExternalValidationV2(
            comparisons=base.comparisons,
            mean_abs_pearson=base.mean_abs_pearson,
            mean_abs_spearman=base.mean_abs_spearman,
            mean_rank_agreement=base.mean_rank_agreement,
            coverage=base.coverage,
            datasets=datasets,
            per_dataset_pearson=per_dataset,
            available=available,
            scipy_used=_scipy_stats is not None,
            notes=notes,
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _composite(values: dict[str, float | None], cols: list[str]) -> float | None:
        present = [values.get(c) for c in cols]
        present = [v for v in present if v is not None]
        if not present:
            return None
        # Single column: return as-is (correlation is scale-invariant). Multi-column
        # composites average the raw values (within-framework columns share scale).
        return float(sum(present) / len(present))

    def _correlate(self, x: list[float], y: list[float]):
        if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
            return None, None, self._rank_agreement(x, y)
        if _scipy_stats is not None:
            try:
                pr = float(_scipy_stats.pearsonr(x, y)[0])
                sr = float(_scipy_stats.spearmanr(x, y)[0])
                return round(pr, 4), round(sr, 4), self._rank_agreement(x, y)
            except Exception:  # noqa: BLE001
                pass
        ax, ay = np.asarray(x, float), np.asarray(y, float)
        pr = float(np.corrcoef(ax, ay)[0, 1])
        sr = float(np.corrcoef(self._ranks(ax), self._ranks(ay))[0, 1])
        return round(pr, 4), round(sr, 4), self._rank_agreement(x, y)

    @staticmethod
    def _ranks(a: np.ndarray) -> np.ndarray:
        order = a.argsort()
        ranks = np.empty_like(order, dtype=float)
        ranks[order] = np.arange(len(a), dtype=float)
        return ranks

    @staticmethod
    def _rank_agreement(x: list[float], y: list[float]) -> float | None:
        n = len(x)
        if n < 3:
            return None
        concordant = total = 0
        for i in range(n):
            for j in range(i + 1, n):
                dx, dy = x[i] - x[j], y[i] - y[j]
                if dx == 0 or dy == 0:
                    continue
                total += 1
                if (dx > 0) == (dy > 0):
                    concordant += 1
        return round(concordant / total, 4) if total else None

    @staticmethod
    def _aggregate(report: ExternalValidationReport) -> None:
        prs = [abs(c.pearson) for c in report.comparisons if c.pearson is not None]
        srs = [abs(c.spearman) for c in report.comparisons if c.spearman is not None]
        ras = [c.rank_agreement for c in report.comparisons if c.rank_agreement is not None]
        report.mean_abs_pearson = round(sum(prs) / len(prs), 4) if prs else None
        report.mean_abs_spearman = round(sum(srs) / len(srs), 4) if srs else None
        report.mean_rank_agreement = round(sum(ras) / len(ras), 4) if ras else None
