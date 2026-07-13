import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Round to a fixed precision, returning a tidy number. */
export function round(n: number | null | undefined, digits = 0): number | null {
  if (n === null || n === undefined || Number.isNaN(n)) return null;
  const f = 10 ** digits;
  return Math.round(n * f) / f;
}

/** Map an ISO3 code to its flag emoji (best-effort; some are not 1:1). */
export function flagEmoji(iso3: string): string {
  const map = ISO3_TO_ISO2[iso3?.toUpperCase()];
  if (!map) return "\u{1F3F3}"; // white flag fallback
  return map
    .toUpperCase()
    .replace(/./g, (c) => String.fromCodePoint(127397 + c.charCodeAt(0)));
}

export function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

// Minimal ISO3 -> ISO2 table (extended on demand; falls back gracefully).
export const ISO3_TO_ISO2: Record<string, string> = {
  KOR: "KR", DEU: "DE", JPN: "JP", USA: "US", CHN: "CN", IND: "IN",
  GBR: "GB", FRA: "FR", ITA: "IT", ESP: "ES", NLD: "NL", SWE: "SE",
  NOR: "NO", DNK: "DK", FIN: "FI", BRA: "BR", MEX: "MX", CAN: "CA",
  AUS: "AU", NZL: "NZ", RUS: "RU", TUR: "TR", SAU: "SA", ARE: "AE",
  EGY: "EG", ZAF: "ZA", NGA: "NG", KEN: "KE", ARG: "AR", CHL: "CL",
  COL: "CO", PER: "PE", IDN: "ID", THA: "TH", VNM: "VN", PHL: "PH",
  MYS: "MY", SGP: "SG", PAK: "PK", BGD: "BD", IRN: "IR", IRQ: "IQ",
  POL: "PL", UKR: "UA", AUT: "AT", CHE: "CH", BEL: "BE", PRT: "PT",
  GRC: "GR", CZE: "CZ", HUN: "HU", ROU: "RO", TWN: "TW", HKG: "HK",
  PRK: "KP", MNG: "MN", LUX: "LU", IRL: "IE", ISR: "IL", QAT: "QA",
};
