# DESIGN_PACKS.md — spec for cutecumber decoration packs 🎨

> Hand this file to designers. It defines exactly what to deliver so their
> kawaii art drops into cutecumber's theming engine without engineering work.
> The system this feeds: decorations are tiled background layers on public
> pages, picked by users in the theme section, validated server-side against
> a registry — never uploaded by end users (see "why curated" at the bottom).

## What a pack is

A folder of SVG decoration tiles plus a tiny manifest:

```
packs/
└── sakura_dreams/              ← pack slug: [a-z0-9_], short
    ├── pack.json
    ├── petals.svg              ← decoration slug: [a-z0-9_]
    ├── blossoms.svg
    └── bunny_clouds.svg
```

`pack.json`:

```json
{
  "name": "sakura dreams",
  "emoji": "🌸",
  "artist": "name or handle, shown as credit",
  "mode": "full_color",
  "decorations": ["petals", "blossoms", "bunny_clouds"]
}
```

Max 12 decorations per pack — the picker has to stay cozy, not become a
spreadsheet.

## The tile format (the important part)

- **SVG only.** No PNG/JPG, no embedded raster images, no external
  references, no `<script>`, no `<foreignObject>`, no event attributes.
  Files failing this are rejected by an automated check, not a human.
- **Canvas: 130×130 viewBox**, transparent background. The tile repeats
  across the whole page background, so it must look good tiled — scatter
  2–3 motifs at different sizes/rotations and keep generous empty space
  (motifs covering ~15–25% of the tile reads "decorated", more reads "busy").
- **≤ 8 KB per file after optimization** (run through SVGO or similar).
  Budget context: an entire cutecumber page is ~2 KB gzipped; one decoration
  may not weigh more than four pages.
- **Two color modes** (declared per pack in `pack.json`):
  - `accent_tinted`: draw in ONE flat color (any — it gets replaced by the
    user's accent color at ~40% opacity). Best for subtle pattern packs.
  - `full_color`: fixed palette, your art exactly as drawn. MUST read well on
    both light pastels (#fff5f7-ish) and the dark theme (#232338). Soft
    outlines or a subtle light halo around motifs usually solves both.
- Motifs sit at low visual intensity — they're wallpaper behind a person's
  name and links, never competing with them.

## What we'd love (direction, not orders)

Kawaii in the soft-web sense: sakura, mushrooms, frogs, bows, sparkles, moons
and stars, koi, strawberries, tea things, tiny ghosts. Rounded, gentle,
slightly imperfect beats geometric-perfect. Think sticker sheet, not icon set.

## Future (so art can anticipate it, not block on it)

- **Avatar sets**: same pipeline, 1 motif per file, square — designer-made
  kawaii avatars as an alternative to emoji/photo avatars.
- **Paid packs**: packs are the natural paid unit later (free tier keeps a
  generous starter set). Artist credit ships with the pack either way.

## Why curated, not user-uploaded

SVG is code-adjacent (it can carry scripts), uploads need moderation, and
every byte lands on the world's pages — so end users pick from packs, they
don't upload them. Pack submission goes through this spec and the automated
checks; that keeps "anyone's page loads in a blink" true forever.
