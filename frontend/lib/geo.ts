import type { CountryFeature, SelectionInfo } from "@/components/CountryGlobe";

const WORLD_TOPO_URL =
  "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

const NUMERIC_TO_ISO3: Record<number, string> = {
  4: "AFG", 8: "ALB", 12: "DZA", 20: "AND", 24: "AGO", 32: "ARG", 36: "AUS",
  40: "AUT", 50: "BGD", 56: "BEL", 64: "BTN", 68: "BOL", 76: "BRA", 100: "BGR",
  104: "MMR", 116: "KHM", 120: "CMR", 124: "CAN", 140: "CAF", 144: "LKA",
  152: "CHL", 156: "CHN", 170: "COL", 178: "COG", 180: "COD", 188: "CRI",
  191: "HRV", 192: "CUB", 196: "CYP", 203: "CZE", 208: "DNK", 214: "DOM",
  218: "ECU", 818: "EGY", 222: "SLV", 231: "ETH", 246: "FIN", 250: "FRA",
  266: "GAB", 276: "DEU", 288: "GHA", 300: "GRC", 320: "GTM", 332: "HTI",
  340: "HND", 348: "HUN", 356: "IND", 360: "IDN", 364: "IRN", 368: "IRQ",
  372: "IRL", 376: "ISR", 380: "ITA", 388: "JAM", 392: "JPN", 400: "JOR",
  398: "KAZ", 404: "KEN", 408: "PRK", 410: "KOR", 414: "KWT", 418: "LAO",
  422: "LBN", 430: "LBR", 434: "LBY", 440: "LTU", 442: "LUX", 458: "MYS",
  466: "MLI", 484: "MEX", 496: "MNG", 504: "MAR", 508: "MOZ", 516: "NAM",
  524: "NPL", 528: "NLD", 554: "NZL", 558: "NIC", 566: "NGA", 578: "NOR",
  586: "PAK", 591: "PAN", 598: "PNG", 600: "PRY", 604: "PER", 608: "PHL",
  616: "POL", 620: "PRT", 634: "QAT", 642: "ROU", 643: "RUS", 682: "SAU",
  686: "SEN", 694: "SLE", 706: "SOM", 710: "ZAF", 724: "ESP", 729: "SDN",
  752: "SWE", 756: "CHE", 760: "SYR", 762: "TJK", 764: "THA", 788: "TUN",
  792: "TUR", 800: "UGA", 804: "UKR", 784: "ARE", 826: "GBR", 840: "USA",
  858: "URY", 860: "UZB", 862: "VEN", 704: "VNM", 887: "YEM", 894: "ZMB",
  716: "ZWE",
};

let cachedFeatures: CountryFeature[] | null = null;
let cachedNeighborsMap: Map<number, number[]> | null = null;

export async function getSelectionInfoByIso3(
  targetIso3: string
): Promise<SelectionInfo | null> {
  if (!cachedFeatures || !cachedNeighborsMap) {
    const res = await fetch(WORLD_TOPO_URL);
    const topo = await res.json();
    const { feature, neighbors } = await import("topojson-client");
    const geo = topo.objects.countries;
    const fc = feature(topo, geo) as unknown as { features: CountryFeature[] };
    const nbrs = neighbors(geo.geometries as never[]);
    const map = new Map<number, number[]>();
    nbrs.forEach((arr: number[], i: number) => map.set(i, arr));
    cachedFeatures = fc.features;
    cachedNeighborsMap = map;
  }

  const feat = cachedFeatures.find((f) => {
    const numId = typeof f.id === "string" ? parseInt(f.id) : (f.id as number);
    return NUMERIC_TO_ISO3[numId] === targetIso3;
  });

  if (!feat) return null;

  const idx = cachedFeatures.indexOf(feat);
  const nbIdx = cachedNeighborsMap.get(idx) ?? [];
  const nbFeatures = nbIdx.map((i) => cachedFeatures![i]).filter(Boolean);

  return {
    country: feat,
    neighbors: nbFeatures,
    iso3: targetIso3,
  };
}
