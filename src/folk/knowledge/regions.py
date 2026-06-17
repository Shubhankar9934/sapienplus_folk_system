"""Region lookups for neighbour and regional-context analysis."""

from __future__ import annotations

from folk.knowledge.regions_data import ISO3_REGION, REGION_MEMBERS


def region_of(iso3: str) -> str | None:
    return ISO3_REGION.get(iso3.upper())


def region_members(region: str, exclude_iso3: str | None = None) -> list[str]:
    members = REGION_MEMBERS.get(region, [])
    if exclude_iso3:
        return [m for m in members if m != exclude_iso3]
    return list(members)


def regional_neighbours(iso3: str) -> list[str]:
    """ISO3s sharing the same region (excluding self)."""
    region = region_of(iso3)
    if region is None:
        return []
    return region_members(region, exclude_iso3=iso3.upper())


def all_regions() -> list[str]:
    return list(REGION_MEMBERS.keys())
