"use client";

/**
 * Simple circular badge showing the country's location.
 * Matches the flat, 2D style from the reference design.
 */
export function CountryGlobeBadge({ iso3 }: { iso3: string }) {
  // Relative position mapping for visual centering (x, y as percentages)
  const POSITION_MAP: Record<string, { x: number; y: number }> = {
    // Africa
    DZA: { x: 52, y: 35 }, // Algeria
    EGY: { x: 56, y: 40 }, // Egypt
    ZAF: { x: 55, y: 75 }, // South Africa
    NGA: { x: 51, y: 48 }, // Nigeria
    KEN: { x: 58, y: 52 }, // Kenya
    MAR: { x: 48, y: 35 }, // Morocco
    
    // Europe
    GBR: { x: 49, y: 28 }, // United Kingdom
    FRA: { x: 51, y: 32 }, // France
    DEU: { x: 53, y: 29 }, // Germany
    ITA: { x: 53, y: 35 }, // Italy
    ESP: { x: 49, y: 36 }, // Spain
    POL: { x: 55, y: 29 }, // Poland
    NLD: { x: 51, y: 28 }, // Netherlands
    SWE: { x: 54, y: 24 }, // Sweden
    NOR: { x: 52, y: 22 }, // Norway
    FIN: { x: 56, y: 22 }, // Finland
    GRC: { x: 55, y: 37 }, // Greece
    PRT: { x: 48, y: 37 }, // Portugal
    
    // Asia
    CHN: { x: 72, y: 38 }, // China
    IND: { x: 70, y: 45 }, // India
    JPN: { x: 82, y: 38 }, // Japan
    KOR: { x: 78, y: 37 }, // South Korea
    THA: { x: 73, y: 48 }, // Thailand
    VNM: { x: 74, y: 46 }, // Vietnam
    IDN: { x: 76, y: 54 }, // Indonesia
    PAK: { x: 68, y: 42 }, // Pakistan
    BGD: { x: 72, y: 45 }, // Bangladesh
    PHL: { x: 78, y: 47 }, // Philippines
    MYS: { x: 74, y: 51 }, // Malaysia
    SGP: { x: 74, y: 52 }, // Singapore
    IRN: { x: 62, y: 40 }, // Iran
    TUR: { x: 57, y: 37 }, // Turkey
    SAU: { x: 60, y: 43 }, // Saudi Arabia
    ISR: { x: 57, y: 41 }, // Israel
    
    // Americas
    USA: { x: 25, y: 42 }, // United States
    CAN: { x: 23, y: 32 }, // Canada
    MEX: { x: 22, y: 45 }, // Mexico
    BRA: { x: 35, y: 65 }, // Brazil
    ARG: { x: 32, y: 75 }, // Argentina
    CHL: { x: 30, y: 73 }, // Chile
    COL: { x: 28, y: 51 }, // Colombia
    PER: { x: 28, y: 62 }, // Peru
    
    // Oceania
    AUS: { x: 78, y: 75 }, // Australia
    NZL: { x: 88, y: 80 }, // New Zealand
    
    // Other
    RUS: { x: 65, y: 25 }, // Russia
    UKR: { x: 57, y: 32 }, // Ukraine
  };

  const pos = POSITION_MAP[iso3] || { x: 50, y: 50 };

  return (
    <div className="relative inline-block h-20 w-20">
      {/* Base circle - light background */}
      <div className="absolute inset-0 rounded-full bg-gradient-to-br from-[#f5f5f5] to-[#e5e5e5] dark:from-[#2a2d32] dark:to-[#1a1c20]" />
      
      {/* Subtle border */}
      <div className="absolute inset-0 rounded-full border border-ink/10 dark:border-white/10" />
      
      {/* Country marker dot */}
      <div 
        className="absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#e14b3c]"
        style={{ 
          left: `${pos.x}%`, 
          top: `${pos.y}%`,
          boxShadow: '0 0 8px rgba(225, 75, 60, 0.6)'
        }}
      />
      
      {/* Subtle blue accent dot (optional, top-right) */}
      <div className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-[#5b8def] opacity-60" />
    </div>
  );
}
