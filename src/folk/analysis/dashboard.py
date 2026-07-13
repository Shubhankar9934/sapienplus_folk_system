"""Council Quality Dashboard builder (Req 7).

Aggregates the council-intelligence-upgrade signals into a single run-level
scorecard and evaluates the success targets:
  - specialist influence > 25%
  - reasoning diversity > 0.5
  - external validation available
  - council value measurable
"""

from __future__ import annotations

import statistics

from folk.config import get_settings
from folk.models.dashboard import CouncilQualityDashboard
from folk.models.profile import CountryProfile
from folk.models.validation import ValidationReport


class CouncilQualityDashboardBuilder:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build(
        self, report: ValidationReport, profiles: list[CountryProfile]
    ) -> CouncilQualityDashboard:
        influence_weights = [r.specialist_influence_weight
                             for p in profiles for r in p.specialist_influence_records]
        influence_pct = round(statistics.mean(influence_weights) * 100, 2) if influence_weights else 0.0

        score_divs = [p.council_diversity_v2.score_diversity
                      for p in profiles if p.council_diversity_v2]
        challenge_ints = [p.council_diversity_v2.challenge_intensity
                          for p in profiles if p.council_diversity_v2]
        source_divs = [p.council_diversity_v2.source_diversity
                       for p in profiles if p.council_diversity_v2]
        reasoning_divs = [p.council_diversity_v2.reasoning_diversity
                          for p in profiles if p.council_diversity_v2]

        evidence_quality = self._evidence_quality(profiles)

        council_value = report.council_impact_v2.council_value_score if report.council_impact_v2 else 0.0
        external_score = None
        if report.external_validation_v2 is not None:
            external_score = report.external_validation_v2.mean_abs_pearson
        elif report.external_validation is not None:
            external_score = report.external_validation.mean_abs_pearson

        dashboard = CouncilQualityDashboard(
            total_countries=len(profiles),
            specialist_influence_pct=influence_pct,
            disagreement_rate=round(statistics.mean(score_divs), 4) if score_divs else 0.0,
            challenge_intensity=round(statistics.mean(challenge_ints), 4) if challenge_ints else 0.0,
            evidence_quality=evidence_quality,
            evidence_diversity=round(statistics.mean(source_divs), 4) if source_divs else 0.0,
            reasoning_diversity=round(statistics.mean(reasoning_divs), 4) if reasoning_divs else 0.0,
            council_value_score=round(council_value, 4),
            external_validation_score=external_score,
        )

        external_available = (report.external_validation_v2 is not None
                              and report.external_validation_v2.available)
        council_value_measurable = report.council_impact_v2 is not None
        targets = {
            "specialist_influence_over_25pct": influence_pct > 25.0,
            "reasoning_diversity_over_0_5": dashboard.reasoning_diversity > 0.5,
            "external_validation_available": external_available,
            "council_value_measurable": council_value_measurable,
        }
        dashboard.targets_met = targets
        dashboard.all_targets_met = all(targets.values())
        dashboard.notes = [f"Unmet target: {k}" for k, v in targets.items() if not v]
        return dashboard

    # ------------------------------------------------------------------ #
    @staticmethod
    def _evidence_quality(profiles: list[CountryProfile]) -> float:
        scores: list[float] = []
        for p in profiles:
            for pack in p.specialist_evidence_packs:
                for s in pack.sources:
                    scores.append(s.verification_score or s.source_quality)
        return round(statistics.mean(scores), 4) if scores else 0.0
