"""In-memory data store for the FOLK web API.

Reads ONLY the culture-first deliverables the pipeline writes:
- ``outputs/countries/{ISO3}.json`` - one self-contained document per country
  (cultural_profile + resolved sources + methodology score details), and
- ``outputs/index.json`` - the slim country list + global stats.

Each per-country doc is flattened into an ISO3-keyed ``profiles`` index whose
shape the analytics + app layers already understand (``final_scores``,
``region``, ``decision_explanations``, ``references``, ``adjustment_log``), plus
``cultural_profile`` and ``sources`` for the culture-first endpoints. Specialist
and intelligence sub-objects are split out so the council/evidence endpoints and
cross-country analytics need nothing else.

Design goals:
- **Tolerant**: any missing/corrupt file is skipped, not fatal.
- **Cheap reload**: :meth:`DataStore.load` rebuilds every index from disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from folk.config import get_settings
from folk.utils.logging import get_logger

log = get_logger()

F_INDEX = "index.json"
COUNTRIES_SUBDIR = "countries"


def _read_json(path: Path) -> Any | None:
    """Read a JSON file, returning ``None`` on any error (missing/corrupt)."""
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # pragma: no cover - defensive
        log.warning(f"API loader: could not read {path.name}: {exc}")
        return None


class DataStore:
    """Holds the per-country docs + index in memory, indexed for fast composition."""

    def __init__(self, outputs_dir: Path | None = None) -> None:
        self.dir = outputs_dir or get_settings().outputs_dir
        # Per-country indexes (iso3 -> record).
        self.docs: dict[str, dict] = {}          # raw per-country documents
        self.profiles: dict[str, dict] = {}      # flattened (methodology + identity)
        self.cultural: dict[str, dict] = {}       # cultural_profile per country
        self.sources_by_iso: dict[str, list] = {}
        self.specialist: dict[str, dict] = {}
        self.intelligence: dict[str, dict] = {}
        # Global artifacts.
        self.index: dict = {}
        self.stats: dict = {}
        self.iso_order: list[str] = []
        self._loaded = False

    # ------------------------------------------------------------------ #
    def load(self) -> "DataStore":
        """(Re)load every artifact from ``outputs/``. Safe to call repeatedly."""
        d = self.dir
        self.docs = {}
        self.profiles = {}
        self.cultural = {}
        self.sources_by_iso = {}
        self.specialist = {}
        self.intelligence = {}

        index = _read_json(d / F_INDEX) or {}
        self.index = index
        self.stats = index.get("stats") or {}
        ordered = [c.get("iso3", "").upper()
                   for c in index.get("countries") or [] if c.get("iso3")]

        countries_dir = d / COUNTRIES_SUBDIR
        # Stale-output fix (Req 12): when index.json exists, ingest ONLY the
        # countries it lists - never orphan JSONs left from earlier runs. Fall
        # back to a directory glob only when index.json has no country list.
        if ordered:
            for iso in ordered:
                doc = _read_json(countries_dir / f"{iso}.json")
                if isinstance(doc, dict):
                    self._ingest((doc.get("iso3") or iso).upper(), doc)
        else:
            files = sorted(countries_dir.glob("*.json")) if countries_dir.exists() else []
            for path in files:
                doc = _read_json(path)
                if not isinstance(doc, dict):
                    continue
                iso = (doc.get("iso3") or path.stem).upper()
                self._ingest(iso, doc)

        # Stable ordering: index order first, then any extra docs.
        self.iso_order = [i for i in ordered if i in self.profiles]
        self.iso_order += [i for i in self.profiles if i not in self.iso_order]

        self._loaded = True
        log.info(f"API data store loaded: {len(self.profiles)} countries from {d}")
        return self

    def _ingest(self, iso: str, doc: dict) -> None:
        self.docs[iso] = doc
        methodology = doc.get("methodology") or {}
        cultural = doc.get("cultural_profile") or {}
        self.cultural[iso] = cultural
        self.sources_by_iso[iso] = doc.get("sources") or []
        self.specialist[iso] = methodology.get("specialist") or {}
        self.intelligence[iso] = methodology.get("intelligence_card") or {}

        # Flattened profile shape the analytics + app layers expect.
        profile = {
            "iso3": iso,
            "country": doc.get("country") or iso,
            "region": doc.get("region"),
            "data_status": doc.get("data_status"),
            "record_type": doc.get("record_type"),
            "processing_date": doc.get("processing_date"),
            "final_scores": methodology.get("final_scores") or {},
            "baseline_scores": methodology.get("baseline_scores") or {},
            "confidence_intervals": methodology.get("confidence_intervals") or {},
            "adjustment_log": methodology.get("adjustment_log") or [],
            "decision_explanations": methodology.get("decision_explanations") or [],
            "neighbours": methodology.get("neighbours") or [],
            "anchor_positions": methodology.get("anchor_positions") or [],
            "calibration_results": methodology.get("calibration_results") or [],
            "references": methodology.get("references") or [],
            "cultural_profile": cultural,
        }
        self.profiles[iso] = profile

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def country_count(self) -> int:
        return len(self.profiles)

    # ------------------------------------------------------------------ #
    # Convenience accessors used by the analytics + app layers.
    # ------------------------------------------------------------------ #
    def has(self, iso3: str) -> bool:
        return iso3.upper() in self.profiles

    def profile(self, iso3: str) -> dict | None:
        return self.profiles.get(iso3.upper())

    def doc(self, iso3: str) -> dict | None:
        return self.docs.get(iso3.upper())

    def cultural_profile(self, iso3: str) -> dict | None:
        return self.cultural.get(iso3.upper())

    def sources(self, iso3: str) -> list:
        return self.sources_by_iso.get(iso3.upper()) or []

    def intel(self, iso3: str) -> dict | None:
        return self.intelligence.get(iso3.upper())

    def specialist_for(self, iso3: str) -> dict | None:
        return self.specialist.get(iso3.upper())

    def all_profiles(self) -> list[dict]:
        """Profiles in stable order (index order, then any extras)."""
        if self.iso_order:
            return [self.profiles[i] for i in self.iso_order if i in self.profiles]
        return list(self.profiles.values())


# Module-level singleton, created/loaded by the app on startup.
_STORE: DataStore | None = None


def get_store() -> DataStore:
    """Return the loaded singleton store, loading it on first use."""
    global _STORE
    if _STORE is None:
        _STORE = DataStore().load()
    return _STORE


def reload_store() -> DataStore:
    """Force a fresh reload of the singleton store from disk."""
    global _STORE
    _STORE = DataStore().load()
    return _STORE
