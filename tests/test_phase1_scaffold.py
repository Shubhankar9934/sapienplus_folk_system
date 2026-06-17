"""Phase 1 - verify scaffold, config loading, and methodology constants."""

from __future__ import annotations

import json

import yaml

from folk.config import get_settings


def test_settings_load():
    s = get_settings()
    assert s.score_min == 3
    assert s.score_max == 97
    assert s.dataset_path.name.endswith(".xlsx")


def test_anchors_config():
    s = get_settings()
    anchors = yaml.safe_load(s.anchors_path.read_text(encoding="utf-8"))["anchors"]
    assert anchors["KOR"]["locked"] == {"d1": 50}
    assert anchors["TUR"]["locked"] == {"d2": 50, "d4": 50}
    assert anchors["COL"]["locked"] == {"d3": 50}


def test_framework_signal_map_overrides():
    s = get_settings()
    cfg = yaml.safe_load(s.framework_signal_map_path.read_text(encoding="utf-8"))
    mappings = cfg["mappings"]

    # GLOBE Performance Orientation must map to D4 only, never D2.
    po = mappings["globe_performance_orientation"]
    assert all(m["dimension"] == "D4" for m in po)

    # GLOBE Uncertainty Avoidance must map to D1 (not D3).
    guai = mappings["globe_uncertainty_avoidance"]
    assert all(m["dimension"] == "D1" for m in guai)

    # Dimension anchor strength encodes uneven anchoring.
    das = cfg["dimension_anchor_strength"]
    assert das["D1"] == 1.0 and das["D2"] == 1.0
    assert das["D3"] == 0.8 and das["D4"] == 0.8


def test_extension_countries_list():
    s = get_settings()
    data = json.loads(s.extension_list_path.read_text(encoding="utf-8"))
    countries = data["countries"]
    assert len(countries) == 26
    isos = {c["iso3"] for c in countries}
    assert {"PRY", "BHR", "MUS", "WSM", "TON", "SYC"} <= isos


def test_prompts_file_present():
    s = get_settings()
    assert s.prompts_path.exists()
    text = s.prompts_path.read_text(encoding="utf-8")
    assert "SHARED_SYSTEM_PREAMBLE" in text
    assert "Devil's Advocate" in text
