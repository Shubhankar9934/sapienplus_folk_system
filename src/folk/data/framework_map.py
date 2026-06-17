"""Declarative column map for the input dataset.

Maps the Excel columns to FOLK dimensions and the five frameworks. Centralised
so the loader, normalizer, and signal analyzer share one source of truth.
"""

from __future__ import annotations

from folk.models.enums import Dimension, Framework

ISO3_COL = "iso3"
COUNTRY_COL = "country_standard"
CASCADE_STEP_COL = "cascade_step"

# Dimension -> (score column, ci_lo column, ci_hi column)
DIMENSION_COLUMNS: dict[Dimension, tuple[str, str, str]] = {
    Dimension.D1: (
        "factor_1_identity_scaled",
        "factor_1_identity_scaled_ci_lo",
        "factor_1_identity_scaled_ci_hi",
    ),
    Dimension.D2: (
        "factor_2_expression_scaled",
        "factor_2_expression_scaled_ci_lo",
        "factor_2_expression_scaled_ci_hi",
    ),
    Dimension.D3: (
        "factor_3_structure_scaled",
        "factor_3_structure_scaled_ci_lo",
        "factor_3_structure_scaled_ci_hi",
    ),
    Dimension.D4: (
        "factor_4_drive_scaled",
        "factor_4_drive_scaled_ci_lo",
        "factor_4_drive_scaled_ci_hi",
    ),
}

# Framework -> ordered list of its source columns.
FRAMEWORK_COLUMNS: dict[Framework, list[str]] = {
    Framework.HOFSTEDE: [
        "hofstede_power_distance",
        "hofstede_individualism",
        "hofstede_masculinity",
        "hofstede_uncertainty_avoidance",
        "hofstede_long_term_orientation",
        "hofstede_indulgence",
    ],
    Framework.GLOBE: [
        "globe_performance_orientation",
        "globe_assertiveness",
        "globe_future_orientation",
        "globe_humane_orientation",
        "globe_institutional_collectivism",
        "globe_in_group_collectivism",
        "globe_gender_egalitarianism",
        "globe_power_distance",
        "globe_uncertainty_avoidance",
    ],
    Framework.SCHWARTZ: [
        "schwartz_harmony",
        "schwartz_embeddedness",
        "schwartz_hierarchy",
        "schwartz_mastery",
        "schwartz_affective_autonomy",
        "schwartz_intellectual_autonomy",
        "schwartz_egalitarianism",
    ],
    Framework.TROMPENAARS: [
        "trompenaars_particularism_universalism",
        "trompenaars_communitarianism_individualism",
        "trompenaars_diffuse_specific",
        "trompenaars_affective_neutral",
        "trompenaars_ascription_achievement",
        "trompenaars_future_past",
        "trompenaars_synchronic_sequential",
        "trompenaars_external_internal",
    ],
    Framework.WVS: [
        "wvs_defiance",
        "wvs_disbelief",
        "wvs_relativism",
        "wvs_scepticism",
        "wvs_autonomy",
        "wvs_equality",
        "wvs_choice",
        "wvs_voice",
    ],
}


def all_framework_columns() -> list[str]:
    cols: list[str] = []
    for fw_cols in FRAMEWORK_COLUMNS.values():
        cols.extend(fw_cols)
    return cols
