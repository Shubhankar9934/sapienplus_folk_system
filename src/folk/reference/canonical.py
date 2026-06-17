"""Canonical citations for the five source frameworks.

Because the FOLK scores derive directly from these datasets, attaching the
primary work for whichever framework contributed evidence is academically
defensible (and verifiable). Used by agents/integrator in mock mode and as a
floor in live mode.
"""

from __future__ import annotations

from folk.models.enums import Dimension, Framework, SourceType
from folk.models.reference import ReferenceRecord

_CANONICAL: dict[Framework, dict] = {
    Framework.HOFSTEDE: {
        "citation": "Hofstede, G. (2001). Culture's Consequences (2nd ed.). Thousand Oaks, CA: Sage.",
        "source_type": SourceType.ACADEMIC_BOOK,
        "url_or_doi": "https://doi.org/10.4135/9781483327679",
    },
    Framework.GLOBE: {
        "citation": (
            "House, R. J., Hanges, P. J., Javidan, M., Dorfman, P. W., & Gupta, V. (2004). "
            "Culture, Leadership, and Organizations: The GLOBE Study of 62 Societies. Sage."
        ),
        "source_type": SourceType.ACADEMIC_BOOK,
        "url_or_doi": None,
    },
    Framework.SCHWARTZ: {
        "citation": (
            "Schwartz, S. H. (2006). A theory of cultural value orientations: Explication "
            "and applications. Comparative Sociology, 5(2-3), 137-182."
        ),
        "source_type": SourceType.ACADEMIC_JOURNAL,
        "url_or_doi": "https://doi.org/10.1163/156913306778667357",
    },
    Framework.TROMPENAARS: {
        "citation": (
            "Trompenaars, F., & Hampden-Turner, C. (1997). Riding the Waves of Culture: "
            "Understanding Cultural Diversity in Business (2nd ed.). Nicholas Brealey."
        ),
        "source_type": SourceType.ACADEMIC_BOOK,
        "url_or_doi": None,
    },
    Framework.WVS: {
        "citation": (
            "Inglehart, R., et al. (eds.) (2014). World Values Survey: All Rounds - "
            "Country-Pooled Datafile. Madrid: JD Systems Institute."
        ),
        "source_type": SourceType.PRIMARY_DATASET,
        "url_or_doi": "https://www.worldvaluessurvey.org",
    },
}


def reference_for(
    framework: Framework, dimension: Dimension | None = None, direction: str | None = None
) -> ReferenceRecord:
    data = _CANONICAL[framework]
    return ReferenceRecord(
        citation=data["citation"],
        source_type=data["source_type"],
        data_point=f"{framework.value} contribution to {dimension.label}" if dimension else None,
        url_or_doi=data["url_or_doi"],
        folk_dimension=dimension,
        direction=direction,
    )


def references_for_frameworks(
    framework_names: list[str], dimension: Dimension | None = None, direction: str | None = None
) -> list[ReferenceRecord]:
    out = []
    for name in framework_names:
        try:
            fw = Framework(name)
        except ValueError:
            continue
        out.append(reference_for(fw, dimension, direction))
    return out
