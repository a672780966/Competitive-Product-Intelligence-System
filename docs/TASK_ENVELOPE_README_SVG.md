# TaskEnvelope: README SVG Brand Assets

## Source
Codex Planning → `docs/README_SVG_BRAND_PLAN.md`

## Task
1. Create `docs/assets/` directory
2. Write SVG files from Codex design:
   - `docs/assets/cpis-logo.svg` (220×60, ~1.3KB)
   - `docs/assets/cpis-banner.svg` (800×200, ~2.1KB)
3. Modify README title blocks — replace plain text headers with SVG images
4. Verify all 11 checkpoints

## SVG Content

### cpis-logo.svg
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 60" width="220" height="60">
  <defs>
    <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1A73E8"/>
      <stop offset="100%" stop-color="#00BCD4"/>
    </linearGradient>
  </defs>
  <polygon points="25,5 45,15 45,35 25,45 5,35 5,15" fill="none" stroke="url(#logoGrad)" stroke-width="2.5"/>
  <polygon points="25,12 38,18 38,30 25,36 12,30 12,18" fill="url(#logoGrad)" opacity="0.12"/>
  <circle cx="25" cy="24" r="4" fill="url(#logoGrad)"/>
  <circle cx="12" cy="18" r="2" fill="#00BCD4"/>
  <circle cx="38" cy="18" r="2" fill="#00BCD4"/>
  <circle cx="12" cy="30" r="2" fill="#00BCD4"/>
  <circle cx="38" cy="30" r="2" fill="#00BCD4"/>
  <text x="58" y="30" font-family="Arial,Helvetica,sans-serif" font-size="24" font-weight="bold" fill="#0F1B2D">
    <tspan fill="url(#logoGrad)">C</tspan>P<tspan fill="url(#logoGrad)">I</tspan>S
  </text>
  <text x="58" y="46" font-family="Arial,Helvetica,sans-serif" font-size="9" fill="#667788" letter-spacing="1.5">
    INTELLIGENCE PLATFORM
  </text>
</svg>
```

### cpis-banner.svg
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200" width="800" height="200">
  <defs>
    <linearGradient id="bannerBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0A1628"/>
      <stop offset="100%" stop-color="#152238"/>
    </linearGradient>
    <linearGradient id="bannerAccent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#1A73E8"/>
      <stop offset="100%" stop-color="#00BCD4"/>
    </linearGradient>
    <linearGradient id="bannerGlow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1A73E8" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#00BCD4" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="800" height="200" fill="url(#bannerBg)" rx="8"/>
  <line x1="0" y1="50" x2="800" y2="50" stroke="#1A2A4A" stroke-width="0.5"/>
  <line x1="0" y1="100" x2="800" y2="100" stroke="#1A2A4A" stroke-width="0.5"/>
  <line x1="0" y1="150" x2="800" y2="150" stroke="#1A2A4A" stroke-width="0.5"/>
  <path d="M 0,185 Q 200,165 400,185 T 800,185" fill="none" stroke="url(#bannerGlow)" stroke-width="1"/>
  <path d="M 0,175 Q 150,195 350,175 T 800,175" fill="none" stroke="#1A73E8" stroke-width="0.5" opacity="0.25"/>
  <polygon points="50,100 65,108 65,124 50,132 35,124 35,108" fill="none" stroke="url(#bannerAccent)" stroke-width="2"/>
  <circle cx="50" cy="116" r="3" fill="url(#bannerAccent)"/>
  <text x="85" y="78" font-family="Arial,Helvetica,sans-serif" font-size="36" font-weight="bold" fill="#FFFFFF">CPIS V1</text>
  <text x="85" y="112" font-family="Arial,Helvetica,sans-serif" font-size="16" fill="#D0D8E0">企业 AI 竞品情报平台</text>
  <text x="85" y="136" font-family="Arial,Helvetica,sans-serif" font-size="13" fill="#7A8A9A">AI-Powered Competitive Product Intelligence Platform</text>
  <rect x="85" y="150" width="630" height="28" rx="14" fill="#1A2A4A" opacity="0.8"/>
  <text x="100" y="168" font-family="Arial,Helvetica,sans-serif" font-size="11" fill="#7AACDD">
    Discovery · Collection · Analysis · Feishu · MCP
  </text>
</svg>
```

## README Modifications

### README.md (from repo root)
Replace lines 5-11 (the plain text `<p>` title block) with:
```html
<p align="center">
  <img src="docs/assets/cpis-logo.svg" alt="CPIS Logo" width="400">
</p>

<p align="center">
  <img src="docs/assets/cpis-banner.svg" alt="CPIS V1 Banner" width="800">
</p>
```

### docs/README.en.md
Replace lines 5-11 with same but path `assets/cpis-logo.svg` and `assets/cpis-banner.svg`

### docs/README.ja.md
Replace lines 5-11 with same but path `assets/cpis-logo.svg` and `assets/cpis-banner.svg`

### docs/README.ko.md
Replace lines 5-11 with same but path `assets/cpis-logo.svg` and `assets/cpis-banner.svg`

## Verification (11 checkpoints)
1. SVG XML valid
2. SVG ≤ 5KB each
3. No `<image>` tags or external `href`
4. No `data:image` base64
5. No `base64` anywhere
6. README paths correct: `docs/assets/...` vs `assets/...`
7. All README src files exist
8. No marketing overclaim
9. Language switcher intact
10. No third-party trademarks
11. Chinese README content preserved
