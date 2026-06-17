"""Bundled region / cultural-cluster membership for all base + extension ISO3 codes.

Grouping blends geography and cultural cluster (Nordic, Gulf, East Asia, etc.) so
neighbour and regional-coherence analysis has a static, citable basis. Extension
ISO3 codes are included so the analogue engine can find scored regional neighbours.
"""

from __future__ import annotations

REGION_MEMBERS: dict[str, list[str]] = {
    "North America": ["USA", "CAN"],
    "Nordic": ["DNK", "FIN", "ISL", "NOR", "SWE"],
    "Western Europe": ["AUT", "BEL", "CHE", "DEU", "FRA", "IRL", "LUX", "NLD", "GBR",
                        "LIE", "AND", "NIR"],
    "Southern Europe": ["ESP", "ITA", "PRT", "GRC", "MLT", "CYP"],
    "Eastern Europe": ["POL", "CZE", "SVK", "HUN", "ROU", "BGR", "HRV", "SVN", "SRB",
                        "BIH", "MKD", "MNE", "ALB", "EST", "LVA", "LTU"],
    "Former Soviet": ["BLR", "UKR", "MDA", "RUS", "ARM", "AZE", "GEO", "KAZ", "KGZ",
                       "TJK", "TKM", "UZB"],
    "East Asia": ["CHN", "JPN", "KOR", "PRK", "TWN", "HKG", "MAC", "MNG"],
    "Southeast Asia": ["IDN", "MYS", "PHL", "SGP", "THA", "VNM", "KHM", "LAO", "MMR",
                        "BRN", "TLS"],
    "South Asia": ["IND", "PAK", "BGD", "LKA", "NPL", "BTN", "AFG", "MDV"],
    "Middle East": ["SAU", "ARE", "QAT", "KWT", "OMN", "BHR", "YEM", "IRQ", "IRN",
                     "JOR", "LBN", "SYR", "ISR", "PSE", "TUR"],
    "North Africa": ["EGY", "LBY", "TUN", "DZA", "MAR", "SDN"],
    "West Africa": ["NGA", "GHA", "SEN", "CIV", "MLI", "BFA", "BEN", "TGO", "NER",
                     "GIN", "GMB", "GNB", "SLE", "LBR", "MRT", "CPV", "STP"],
    "Central Africa": ["CMR", "GAB", "COG", "COD", "CAF", "TCD", "GNQ"],
    "East Africa": ["ETH", "KEN", "TZA", "UGA", "RWA", "BDI", "SOM", "DJI", "ERI",
                     "SSD", "MDG", "COM", "SYC", "MUS"],
    "Southern Africa": ["ZAF", "NAM", "BWA", "ZWE", "ZMB", "MWI", "MOZ", "AGO", "LSO",
                         "SWZ"],
    "South America": ["ARG", "BOL", "BRA", "CHL", "COL", "ECU", "GUY", "PER", "PRY",
                       "SUR", "URY", "VEN"],
    "Central America": ["MEX", "CRI", "SLV", "GTM", "HND", "NIC", "PAN", "BLZ"],
    "Caribbean": ["CUB", "DOM", "HTI", "JAM", "PRI", "TTO", "BHS", "ATG", "BRB",
                  "DMA", "GRD", "KNA", "LCA", "VCT"],
    "Oceania": ["FJI", "PNG", "AUS", "NZL", "FSM", "KIR", "MHL", "NRU", "PLW", "WSM",
                "SLB", "TON", "TUV", "VUT"],
}

# iso3 -> region (inverted index)
ISO3_REGION: dict[str, str] = {
    iso: region for region, members in REGION_MEMBERS.items() for iso in members
}
