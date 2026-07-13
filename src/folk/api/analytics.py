"""Cross-country analytics derived from the loaded FOLK artifacts.

Everything here is computed from data the pipeline already produces - no new
modelling. The expensive, dataset-wide pieces (distance matrix, clustering,
distributions) are computed once in :meth:`Analytics.build`; per-country
derivations (evidence strength, council agreement, regional context, source
reliability, confidence breakdown, council impact) are cheap and computed on
demand.

All outputs degrade gracefully when only a handful of countries are present
(e.g. a 2-country smoke test): similarity/uniqueness/archetypes simply report
that more countries are needed rather than producing misleading numbers.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np

from folk.api.loader import DataStore

DIMENSIONS = ("D1", "D2", "D3", "D4")

DIM_META: dict[str, dict[str, str]] = {
    "D1": {"label": "Identity", "low": "Social", "high": "Self"},
    "D2": {"label": "Expression", "low": "Restrained", "high": "Open"},
    "D3": {"label": "Structure", "low": "Fluid", "high": "Certain"},
    "D4": {"label": "Drive", "low": "Accepting", "high": "Striving"},
}

SPECIALIST_LABELS: dict[str, str] = {
    "cultural_anthropologist": "Cultural Anthropologist",
    "institutional_analyst": "Institutional Analyst",
    "historical_analyst": "Historical-Cultural Analyst",
    "statistician": "Statistician",
    "comparativist": "Comparativist",
    "country_specialist": "Country Specialist",
    "skeptic": "Devil's Advocate",
}

# Friendly buckets for reference source_type values.
SOURCE_TYPE_LABELS: dict[str, str] = {
    "academic_journal": "Academic Papers",
    "academic_book": "Books",
    "primary_dataset": "Datasets",
    "government_report": "Government Reports",
    "think_tank": "Think Tanks",
    "news_article": "Journalism",
    "journalism": "Journalism",
    "report": "Reports",
    "website": "Web Sources",
}

# Minimum countries before dataset-wide analytics become meaningful.
_MIN_FOR_SIMILARITY = 3
_MIN_FOR_CLUSTERS = 6

_NUM = r"([0-9]+(?:\.[0-9]+)?)"
_CONF_RE = re.compile(
    rf"coverage={_NUM}.*?agreement={_NUM}.*?evidence={_NUM}.*?stability={_NUM}",
    re.IGNORECASE | re.DOTALL,
)
_SCORE_RE = re.compile(rf"score\s+{_NUM}", re.IGNORECASE)


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def profile_scores(profile: dict) -> dict[str, float]:
    """Extract the four final scores from a profile, when all are present."""
    fs = profile.get("final_scores") or {}
    out: dict[str, float] = {}
    for d in DIMENSIONS:
        v = fs.get(d)
        if isinstance(v, dict) and v.get("score") is not None:
            try:
                out[d] = float(v["score"])
            except (TypeError, ValueError):
                pass
    return out


def _vector(scores: dict[str, float]) -> list[float] | None:
    if all(d in scores for d in DIMENSIONS):
        return [scores[d] for d in DIMENSIONS]
    return None


def archetype_label(centroid: list[float]) -> str:
    """Human-readable cluster label derived deterministically from a centroid.

    Picks the two dimensions that deviate most from the neutral midpoint (50)
    and composes ``<adjective(secondary)> <noun(primary)>`` from them, e.g. a
    centroid high on Drive and low on Identity becomes "Communal Achievers";
    high Identity + high Structure becomes "Structured Individualists".
    """
    d = {dim: centroid[i] for i, dim in enumerate(DIMENSIONS)}

    nouns = {
        ("D1", "high"): "Individualists", ("D1", "low"): "Collectivists",
        ("D2", "high"): "Expressives", ("D2", "low"): "Stoics",
        ("D3", "high"): "Planners", ("D3", "low"): "Improvisers",
        ("D4", "high"): "Achievers", ("D4", "low"): "Easygoers",
    }
    adjs = {
        ("D1", "high"): "Independent", ("D1", "low"): "Communal",
        ("D2", "high"): "Expressive", ("D2", "low"): "Reserved",
        ("D3", "high"): "Structured", ("D3", "low"): "Fluid",
        ("D4", "high"): "Driven", ("D4", "low"): "Relaxed",
    }

    # Rank dimensions by absolute deviation from the midpoint.
    ranked = sorted(DIMENSIONS, key=lambda dim: abs(d[dim] - 50), reverse=True)
    primary = ranked[0]
    if abs(d[primary] - 50) < 8:
        return "Balanced Cultures"

    def pole(dim: str) -> str:
        return "high" if d[dim] >= 50 else "low"

    noun = nouns[(primary, pole(primary))]
    secondary = ranked[1]
    if abs(d[secondary] - 50) >= 8:
        adj = adjs[(secondary, pole(secondary))]
        return f"{adj} {noun}"
    return noun


class Analytics:
    """Dataset-wide analytics over the loaded :class:`DataStore`."""

    def __init__(self, store: DataStore) -> None:
        self.store = store
        self.isos: list[str] = []
        self.vectors: dict[str, list[float]] = {}
        self.matrix: np.ndarray | None = None
        self._max_dist: float = 1.0
        self.similarity: dict[str, dict] = {}
        self.uniqueness: dict[str, float] = {}
        self.archetype_by_iso: dict[str, str] = {}
        self.clusters: list[dict] = []
        # Per-dimension global arrays for percentile placement.
        self._dim_values: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
        # region -> {dim -> mean}
        self._region_means: dict[str, dict[str, float]] = {}

    # ------------------------------------------------------------------ #
    def build(self) -> "Analytics":
        self.isos = []
        self.vectors = {}
        for iso in self.store.iso_order or list(self.store.profiles.keys()):
            prof = self.store.profiles.get(iso)
            if not prof:
                continue
            vec = _vector(profile_scores(prof))
            if vec is not None:
                self.isos.append(iso)
                self.vectors[iso] = vec

        self._build_distance_matrix()
        self._build_similarity_and_uniqueness()
        self._build_distributions()
        self._build_regions()
        self._build_clusters()
        return self

    def _build_distance_matrix(self) -> None:
        if not self.isos:
            self.matrix = None
            return
        # Normalize to 0-1 (scores live on a 3-97 scale) for distance.
        mat = np.array([self.vectors[i] for i in self.isos], dtype=float) / 100.0
        diff = mat[:, None, :] - mat[None, :, :]
        dist = np.sqrt((diff ** 2).sum(axis=2))
        self.matrix = dist
        self._max_dist = float(dist.max()) or 1.0

    def _build_similarity_and_uniqueness(self) -> None:
        self.similarity = {}
        self.uniqueness = {}
        n = len(self.isos)
        if self.matrix is None or n < _MIN_FOR_SIMILARITY:
            return
        mean_dists = []
        for idx, iso in enumerate(self.isos):
            row = self.matrix[idx]
            order = [j for j in np.argsort(row) if j != idx]
            ranked = [
                {
                    "iso3": self.isos[j],
                    "country": self._country_name(self.isos[j]),
                    "similarity": round(_clamp(100.0 * (1.0 - row[j] / self._max_dist)), 1),
                    "distance": round(float(row[j]), 4),
                }
                for j in order
            ]
            self.similarity[iso] = {
                "most_similar": ranked[:5],
                "most_different": list(reversed(ranked[-5:])),
            }
            others = np.delete(row, idx)
            mean_dists.append((iso, float(others.mean())))

        # Uniqueness = percentile of mean-distance-to-others (higher = rarer).
        values = np.array([m for _, m in mean_dists])
        for iso, m in mean_dists:
            pct = float((values <= m).sum()) / len(values) * 100.0
            self.uniqueness[iso] = round(pct, 1)

    def _build_distributions(self) -> None:
        self._dim_values = {d: [] for d in DIMENSIONS}
        for iso in self.isos:
            vec = self.vectors[iso]
            for i, d in enumerate(DIMENSIONS):
                self._dim_values[d].append(vec[i])

    def _build_regions(self) -> None:
        groups: dict[str, dict[str, list[float]]] = {}
        for iso in self.isos:
            prof = self.store.profiles.get(iso) or {}
            region = prof.get("region") or "Unknown"
            scores = profile_scores(prof)
            g = groups.setdefault(region, {d: [] for d in DIMENSIONS})
            for d in DIMENSIONS:
                if d in scores:
                    g[d].append(scores[d])
        self._region_means = {
            region: {d: (float(np.mean(v)) if v else 0.0) for d, v in dims.items()}
            for region, dims in groups.items()
        }

    def _build_clusters(self) -> None:
        self.clusters = []
        self.archetype_by_iso = {}
        n = len(self.isos)
        if n < _MIN_FOR_CLUSTERS:
            return
        try:
            from scipy.cluster.vq import kmeans2
        except ImportError:  # pragma: no cover
            return

        data = np.array([self.vectors[i] for i in self.isos], dtype=float)
        k = max(2, min(8, int(round((n / 2) ** 0.5))))
        k = min(k, n)
        np.random.seed(42)
        try:
            centroids, labels = kmeans2(data, k, minit="++", seed=42, missing="warn")
        except Exception:  # pragma: no cover - clustering fallback
            return

        # Compose deterministic, de-duplicated labels per cluster.
        raw_labels: dict[int, str] = {}
        used: dict[str, int] = {}
        for cidx in range(len(centroids)):
            base = archetype_label(list(centroids[cidx]))
            if base in used:
                used[base] += 1
                label = f"{base} {'I' * (used[base])}"
            else:
                used[base] = 1
                label = base
            raw_labels[cidx] = label

        members: dict[int, list[str]] = {}
        for i, iso in enumerate(self.isos):
            cidx = int(labels[i])
            members.setdefault(cidx, []).append(iso)
            self.archetype_by_iso[iso] = raw_labels.get(cidx, "Balanced Cultures")

        for cidx, isos in sorted(members.items(), key=lambda kv: -len(kv[1])):
            self.clusters.append({
                "label": raw_labels.get(cidx, "Balanced Cultures"),
                "centroid": {d: round(float(centroids[cidx][i]), 1)
                             for i, d in enumerate(DIMENSIONS)},
                "size": len(isos),
                "members": [
                    {"iso3": iso, "country": self._country_name(iso)} for iso in isos
                ],
            })

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _country_name(self, iso: str) -> str:
        prof = self.store.profiles.get(iso) or {}
        return prof.get("country") or iso

    def _confidence_components(self, iso: str) -> dict[str, dict[str, float]]:
        """Parse coverage/agreement/evidence/stability + final per dimension."""
        prof = self.store.profiles.get(iso) or {}
        out: dict[str, dict[str, float]] = {}
        for de in prof.get("decision_explanations") or []:
            dim = de.get("dimension")
            expl = de.get("confidence_explanation") or ""
            if not dim:
                continue
            comps: dict[str, float] = {}
            m = _CONF_RE.search(expl)
            if m:
                comps = {
                    "coverage": round(float(m.group(1)) * 100, 1),
                    "agreement": round(float(m.group(2)) * 100, 1),
                    "evidence": round(float(m.group(3)) * 100, 1),
                    "stability": round(float(m.group(4)) * 100, 1),
                }
            sm = _SCORE_RE.search(expl)
            if sm:
                comps["final"] = round(float(sm.group(1)) * 100, 1)
            if comps:
                out[dim] = comps
        return out

    # ------------------------------------------------------------------ #
    # Public per-country derivations
    # ------------------------------------------------------------------ #
    def evidence_strength(self, iso: str) -> dict[str, Any]:
        """Per-dimension + overall evidence-strength score (0-100)."""
        comps = self._confidence_components(iso)
        intel = self.store.intelligence.get(iso) or {}
        source_counts = {
            dd.get("dimension"): len(dd.get("key_sources") or [])
            for dd in intel.get("dimensions") or []
        }
        per_dim: dict[str, float] = {}
        for dim, c in comps.items():
            blended = (
                0.30 * c.get("evidence", 0)
                + 0.30 * c.get("agreement", 0)
                + 0.20 * c.get("coverage", 0)
                + 0.20 * c.get("stability", 0)
            )
            bonus = min(5.0, source_counts.get(dim, 0) * 1.0)
            per_dim[dim] = round(_clamp(blended + bonus), 1)
        overall = round(float(np.mean(list(per_dim.values()))), 1) if per_dim else None
        return {"overall": overall, "per_dimension": per_dim}

    def confidence_breakdown(self, iso: str) -> dict[str, dict[str, float]]:
        return self._confidence_components(iso)

    def council_agreement(self, iso: str) -> dict[str, Any]:
        """Per-dimension + overall agreement (0-100) from specialist positions."""
        spec = self.store.specialist.get(iso) or {}
        positions = spec.get("positions") or []
        by_dim: dict[str, list[dict]] = {}
        for p in positions:
            dim = p.get("dimension")
            if dim:
                by_dim.setdefault(dim, []).append(p)

        per_dim: dict[str, Any] = {}
        agreements: list[float] = []
        for dim, items in by_dim.items():
            scores = [float(i.get("proposed_score")) for i in items
                      if i.get("proposed_score") is not None]
            if not scores:
                continue
            spread = max(scores) - min(scores)
            # Max meaningful spread on a 3-97 scale is 94.
            agree = round(_clamp(100.0 * (1.0 - spread / 94.0)), 1)
            agreements.append(agree)
            per_dim[dim] = {
                "agreement": agree,
                "spread": round(spread, 1),
                "specialists": [
                    {
                        "specialist": i.get("specialist"),
                        "label": SPECIALIST_LABELS.get(
                            i.get("specialist", ""), i.get("specialist")),
                        "proposed_score": i.get("proposed_score"),
                        "confidence": i.get("confidence"),
                    }
                    for i in items
                ],
            }
        overall = round(float(np.mean(agreements)), 1) if agreements else None
        return {
            "overall": overall,
            "verdict": self._consensus_verdict(overall),
            "per_dimension": per_dim,
        }

    @staticmethod
    def _consensus_verdict(overall: float | None) -> str | None:
        if overall is None:
            return None
        if overall >= 80:
            return "Strong Consensus"
        if overall >= 60:
            return "Moderate Consensus"
        return "High Disagreement"

    def regional_context(self, iso: str) -> dict[str, Any]:
        prof = self.store.profiles.get(iso) or {}
        region = prof.get("region") or "Unknown"
        scores = profile_scores(prof)
        means = self._region_means.get(region, {})
        per_dim: dict[str, Any] = {}
        for d in DIMENSIONS:
            if d in scores and d in means:
                avg = round(means[d], 1)
                per_dim[d] = {
                    "score": round(scores[d], 1),
                    "region_average": avg,
                    "delta": round(scores[d] - avg, 1),
                }
        return {"region": region, "per_dimension": per_dim}

    def global_distribution(self, iso: str) -> dict[str, Any]:
        prof = self.store.profiles.get(iso) or {}
        scores = profile_scores(prof)
        per_dim: dict[str, Any] = {}
        for d in DIMENSIONS:
            values = self._dim_values.get(d, [])
            if d in scores and values:
                arr = np.array(values)
                pct = float((arr <= scores[d]).sum()) / len(arr) * 100.0
                per_dim[d] = {
                    "score": round(scores[d], 1),
                    "percentile": round(pct, 1),
                    "rank": int((arr > scores[d]).sum()) + 1,
                    "total": len(arr),
                }
        return {"per_dimension": per_dim}

    def source_reliability(self, iso: str) -> dict[str, Any]:
        prof = self.store.profiles.get(iso) or {}
        refs = prof.get("references") or []
        counts: dict[str, int] = {}
        verified = 0
        for r in refs:
            stype = r.get("source_type") or "other"
            label = SOURCE_TYPE_LABELS.get(stype, stype.replace("_", " ").title())
            counts[label] = counts.get(label, 0) + 1
            if r.get("verified"):
                verified += 1
        total = len(refs)
        # Average source quality from per-dimension evidence_quality (0-1).
        spec = self.store.specialist.get(iso) or {}
        qualities = [float(rec.get("evidence_quality")) for rec in spec.get("influence_records") or []
                     if rec.get("evidence_quality") is not None]
        avg_quality = round(float(np.mean(qualities)) * 100, 1) if qualities else None
        return {
            "total_sources": total,
            "verified": verified,
            "verified_pct": round(verified / total * 100, 1) if total else 0.0,
            "average_quality": avg_quality,
            "by_type": [{"type": k, "count": v}
                        for k, v in sorted(counts.items(), key=lambda kv: -kv[1])],
        }

    def council_impact(self, iso: str) -> dict[str, Any]:
        """Per-dimension baseline -> final change with the driving reason."""
        prof = self.store.profiles.get(iso) or {}
        adj_by_dim = {a.get("dimension"): a for a in prof.get("adjustment_log") or []}
        per_dim: dict[str, Any] = {}
        for de in prof.get("decision_explanations") or []:
            dim = de.get("dimension")
            if not dim:
                continue
            adj = adj_by_dim.get(dim, {})
            baseline = de.get("baseline_score")
            final = de.get("final_score")
            per_dim[dim] = {
                "baseline": round(float(baseline), 1) if baseline is not None else None,
                "final": final,
                "change": de.get("change_amount"),
                "adjustment_type": de.get("adjustment_type"),
                "reason": adj.get("reason") or de.get("summary"),
            }
        return {"per_dimension": per_dim}

    def rankings(self, dim: str, top_n: int = 10) -> dict[str, Any]:
        """Global highest/lowest for a dimension."""
        entries = []
        for iso in self.isos:
            scores = profile_scores(self.store.profiles.get(iso) or {})
            if dim in scores:
                entries.append({
                    "iso3": iso,
                    "country": self._country_name(iso),
                    "region": (self.store.profiles.get(iso) or {}).get("region"),
                    "score": round(scores[dim], 1),
                })
        ranked = sorted(entries, key=lambda e: e["score"], reverse=True)
        return {
            "dimension": dim,
            "label": DIM_META[dim]["label"],
            "highest": ranked[:top_n],
            "lowest": list(reversed(ranked[-top_n:])) if ranked else [],
        }

    def region_rankings(self, dim: str) -> dict[str, Any]:
        rows = [
            {"region": region, "average": round(means.get(dim, 0.0), 1)}
            for region, means in self._region_means.items()
            if region != "Unknown"
        ]
        rows.sort(key=lambda r: r["average"], reverse=True)
        return {"dimension": dim, "label": DIM_META[dim]["label"], "regions": rows}


# Module-level singleton, rebuilt whenever the store reloads.
_ANALYTICS: Analytics | None = None


def get_analytics(store: DataStore) -> Analytics:
    global _ANALYTICS
    if _ANALYTICS is None or _ANALYTICS.store is not store:
        _ANALYTICS = Analytics(store).build()
    return _ANALYTICS


def rebuild_analytics(store: DataStore) -> Analytics:
    global _ANALYTICS
    _ANALYTICS = Analytics(store).build()
    return _ANALYTICS
