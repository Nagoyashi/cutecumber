# Design refresh v2 — landing + dashboard (spec)

Canonical spec for the **`v0.4.0` design refresh** (milestone `v0.4.0`; issues
#40–#44). It modernizes two surfaces — the public landing (`/`) and the
logged-in dashboard/editor (`/dash`) — keeping the kawaii-minimal brand but
fixing the "plain, centered, empty-on-desktop" feel with a split hero, an
ambient animated brand background, glassy cards, a real top bar, and the drawn
avatar set in the profile picker.

## How to use this doc

The handoff was delivered as HTML/React+Babel **prototypes** — reference only,
**not** production code. The contract is unchanged (`RULES.md`): Flask + Jinja,
**no React / no build step / no CDN**, **zero JS + zero third-party on public
pages**, ≤15 KB gzipped landing, WCAG-AA contrast, no trackers/cookies for
anonymous visitors. Recreate the visuals inside the existing templates:

- Landing → `app/templates/index.html` (self-contained, one inline `<style nonce>`).
- Dashboard → `app/templates/dash_base.html` + `dash_home.html` + `app/static/dash.css` (extend the tokens, don't fork them).
- Ambient background → a single static inline `<svg>` layer, CSS-only motion, `aria-hidden`.
- The prototype's "Tweaks" panel is a design tool — **not shipped**.

The 12 avatar SVGs and brand marks from the bundle are **already in the repo**
(`app/static/avatars/*.svg`, `app/static/favicon.svg`) — byte-identical, no
import needed.

---

## Design tokens

### Colors — UI
| Token | Hex | Use |
|---|---|---|
| green | `#3f5a39` | wordmark, headings, brand text |
| ink | `#3c3c43` | body text (10.4:1 on white) |
| muted | `#6e6e78` | secondary text |
| faint | `#8a8a93` | tertiary / footer |
| accent | `#e58fb1` | primary buttons, links, selection (= strawberry_milk accent) |
| accent-deep | `#d97da2` | accent hover |
| border | `#f0d4de` | card/input borders, dashed dividers |
| bg1 / bg2 | `#fff5f7` / `#f3f9f4` | page gradient `linear-gradient(160deg, bg1, bg2)`, `background-attachment: fixed` |
| err / err-bg | `#a33a52` / `#fdeef0` | dashboard delete button |

### Colors — brand art (motifs & avatars)
body `#8fcb72` · bodyDark `#6da854` · bodyLight `#a9da8d` · flesh `#ecf7df` ·
seed `#cde8b4` · face-ink `#33502e` · blush `#f7b1c8`. (The slice mark colors
are fixed and never themed — RULES.md / DECISIONS #34.)

### Colors — dark preview (midnight_snack, shown in the dashboard preview)
bg gradient `#2d2d49 → #232338` · text `#f1edf9` · muted `#bbb9c7` · bio
`#e7e4f1` · link pill bg `#93d27f`, link pill text `#1c2b18`.

### Theme preset chips (keep in sync with `theme.PRESETS`)
| preset | chip bg | dot |
|---|---|---|
| strawberry_milk | `#fff5f7` | `#e58fb1` |
| matcha_latte | `#f4f9ef` | `#6f9a5d` |
| lavender_haze | `#f7f3fd` | `#7a59c8` |
| cherry_cola | `#fdf1ef` | `#b23350` |
| seafoam | `#eefaf6` | `#1f7d76` |
| midnight_snack | `#232338` | `#f3a7c3` |

### Typography
- **Display / headings / wordmark / section titles:** Fredoka 600,
  `letter-spacing: -0.4px` (titles) → `-0.5px` (wordmark/H1), **lowercase**.
  Self-hosted `app/static/fonts/fredoka-latin-600-normal.woff2`, `font-display: swap`.
  (One font file already loaded — body/UI stays the system stack.)
- **Body / UI / inputs:** `system-ui, -apple-system, "Segoe UI", sans-serif`.
- Scale: landing H1 `clamp(2.3rem, 5vw, 3.4rem)`/lh 1.05; tagline `1.12rem`
  muted; section titles `1.18rem` green; feature H3 `1.05rem`; body `~1rem/1.5`;
  hints `0.85rem` muted.

### Radius / shadows / spacing
- Radius: cards `20px` · inputs & link-rows `12–14px` · buttons/pills `999px` ·
  avatar tiles `16px` (inner img `13px`) · preset chips `50%` · dash preview
  `22px` · landing phone mock `30px`.
- Shadows: card `0 8px 28px rgba(229,143,177,.12)` · landing primary button
  `0 8px 22px rgba(229,143,177,.32)` · phone mock `0 24px 60px rgba(83,52,63,.16)`
  · motif `drop-shadow(0 6px 12px rgba(83,52,63,.05–.06))` · preview avatar
  `0 6px 16px rgba(0,0,0,.25)`.
- Containers: landing shell `max-width:1120px`; dashboard `1080px`; h-padding
  `32px` (→ `20/18px` small). Hero gap `56px`/`40px`. Editor grid
  `minmax(0,1fr) 380px`, gap `22px`, right column `position:sticky; top:22px`.
- Cards: `rgba(255,255,255,0.9); backdrop-filter:blur(8px); 1px solid border;
  radius 20px` + card shadow. (Landing feature cards `rgba(255,255,255,0.82)` + `blur(6px)`.)

---

## Screens

### Landing (`/`)
Three stacked regions in a centered shell:
1. **Top bar** — space-between, padding `24px 0 8px`. Left: slice (40px) +
   "cutecumber" (Fredoka green 1.5rem). Right: `log in` (text link, ink →
   accent-deep hover) + `claim your username` (solid accent pill, white).
2. **Hero** — `grid 1.05fr 0.95fr; gap 56px; padding 64px 0 80px`.
   - Left (`.hero-copy`, max 540px): H1 "the cutest little home for all your
     links"; tagline "one tiny page for your socials, your shop, your
     everything — and one link to share it." (muted, max 30ch); CTA row =
     primary pill `claim your username ✨` + ghost pill `log in`; claim line
     "cutecumber.cc/**you** — if it's free, it's yours" (`you` in green).
   - Right (`.hero-visual`): the example-page preview card (below).
3. **Features** — `grid repeat(4,1fr); gap 16px; padding 8px 0 72px`. Each
   `.feat`: motif icon in a `40×40` rounded-12 `#fff5f7` tile, H3 (Fredoka green
   1.05rem), muted paragraph:
   - leaf → "zero trackers, zero cookies" → "no analytics, no pixels, nothing watching your visitors. ever."
   - sparkle → "honestly, stupidly fast" → "your page is about two kilobytes — done before the tap ends."
   - blossom → "cute that everyone can read" → "every theme passes accessibility contrast. soft, never squinty."
   - sprout → "small, indie, yours" → "no big tech, no ads, nothing about you for sale."
4. **Footer** — centered faint: `privacy · imprint`.

**Preview card (`.phone`):** 290px, white, radius 30px, padding `30px 22px
22px`, phone shadow, centered. Avatar SVG (84×84, radius 22) = `avatars/bun.svg`;
name "mochi" (Fredoka green 1.3rem); "she/her · sticker artist 🌷" (muted
0.86rem); 3 accent pill links; foot "made with 🥒 cutecumber" (faint 0.74rem).
Three tiny decoration motifs in the corners. Gently bobs.

**Responsive:** <880px → one column, visual `order:-1` above copy, features
`repeat(2,1fr)`. ≤520px → features 1-col, shell padding 20px, hide `log in` text
link (pill stays).

### Dashboard (`/dash`, claimed username)
- **Top bar** (max 1080px): slice 36px + wordmark; nav `my page` (active) /
  `account` / `log out` (accent pill).
- **Page bar** (`.pagebar` card): left = "your page is live 🎉" + big URL
  "cutecumber.cc/**rob**" (username in accent-deep, links to public page); right
  = `copy link` (ghost pill) + `visit ↗` (accent pill).
- **Editor** — `grid minmax(0,1fr) 380px; gap 22px; align-items:start`. Left =
  stacked sections; right = sticky preview.

**Left — three `.card.sec` collapsible sections** (native `<details>/<summary>`,
chevron rotates on `[open]`):
1. **your links 🔗** (open): `.linkrow` `grid 28px 50px 1fr` — drag handle `⠿`,
   emoji input (50px), title, url (`grid-column 1/-1`), then right-aligned
   `save` (accent pill) + `delete` (white pill, err text, err-bg border). Below:
   dashed-top add-link form (emoji+title, url full-row, `add link ➕`, hint).
2. **your profile 🌷** (closed): avatar picker = `grid auto-fill minmax(54px,1fr)
   gap 10px` of the 12 `set:` avatars (`.av-pick`: white, `0 0 0 1.5px border`
   ring, radius 16; hover 2px accent ring; selected `.on` 3px accent-deep ring) +
   dashed upload tile (`＋ photo`). Hint "we strip all location data — promise
   🍃". Fields: display name, pronouns (optional), bio; `save my profile 💾`.
3. **your theme 🎨** (closed): `.presets` grid (`auto-fill minmax(92px,1fr)`) of
   the 6 chips (circle swatch + dot + name); selected → 3px accent-deep ring;
   `use this preset ✨`; hint. Keep the existing fine-tune controls, restyled.

**Right — preview** (`.card`, sticky): label "preview 🔍"; in production this
stays the existing `<iframe src="/{username}">` live preview (the prototype fakes
a midnight_snack dark mock).

**Responsive:** ≤979px single column, preview `order:-1` above. ≤520px tighten +
hide active "my page" pill.

---

## Interactions & motion
- **Navigation:** landing CTAs → `/signup`, `/login`; footer → `/privacy`,
  `/imprint`. Dashboard URL/visit → public page; `copy link` → clipboard +
  brief confirmation (progressive enhancement; degrades to a normal link).
  Keep all existing Flask routes/forms.
- **Collapsible sections:** native `<details>/<summary>` styled to tokens;
  chevron is `summary::after` rotating on `[open]`. Default: links open.
- **Selection controls:** avatar + preset are single-select `<input type=radio>`
  + `<label>` (no-JS support); the ring is `input:checked + .swatch`.
- **Hover/focus:** pills darken to accent-deep; ghost pills shift border to
  accent; inputs focus → `border-color:accent; box-shadow:0 0 0 3px
  rgba(229,143,177,.22)`; preserve the AA `:focus-visible` outlines.
- **Motion** (both gated behind `@media (prefers-reduced-motion: no-preference)`,
  default on; no JS toggle):
  - `drift` — float a motif up + slight rotate; preserve its `translate(-50%,
    -50%)` centering offset in the keyframe. Per-motif duration 8–19s, staggered
    delay via inline CSS vars. Dashboard calmer (−22px / +5deg).
  - `bob` — `translateY(0 → −14px → 0)`. Landing watermark 22s + phone card 7s;
    dashboard watermark 22s.

## Ambient background (decorative)
`.ambient { position:fixed; inset:0; z-index:0; pointer-events:none;
overflow:hidden }`; content sits in a `z-index:1` shell. Two parts:
1. **Watermark** — one big slice (~640px) at low opacity (landing `.07`, dash
   `.06`), offset off the bottom-right corner.
2. **Floating motifs** — small brand motifs (`.motif`, positioned by `left/top`
   %) hugging margins/corners so they never sit behind hero text. Sizes 22–96px,
   opacities 0.5–0.7. Landing 11–12 motifs; dashboard 6 (0 = fully clean). Exact
   placements come from the prototype's `FIELD` array.

Render as a **single static inline `<svg>`/sprite layer** (or a few small
repeated SVGs), `aria-hidden`, animated with CSS only — no per-element JS, no
raster.

## State
Server-rendered, no-JS-first. Links/profile/theme CRUD stays on the existing
Flask routes (`theme.py` engine unchanged). With the drawn set, the avatar value
is `set:<name>` (e.g. `set:whiskers`) alongside the `image:<id>` upload kind,
validated against the registry at save AND render. **Default avatar → `set:sprout`**
(replaces `DEFAULT_AVATAR_EMOJI`). Section open state = native `<details open>`.

## Assets
- `app/static/favicon.svg` — slice mark (favicon + top-bar wordmark mark +
  ambient watermark).
- `app/static/avatars/*.svg` — the 12 drawn avatars (`bun` in the landing
  preview, `whiskers` in the dashboard preview).
- **Motifs** (slice, blossom, sparkle, strawberry, frog, cloud, sprout, heart,
  bow, leaf, babyCuke) — canonical source is the handoff's `motifs.jsx`
  (`MOTIF` map); port into a production inline-SVG sprite.
- Font: `fredoka-latin-600-normal.woff2` (already in repo).

## Next phase (not in this cycle)
Apply the system to the **public profile pages** (`/<username>`) and **auth
screens** (`/login`, `/signup`, claim) — designs to follow. Auth reuses the
landing shell; public pages keep their own ultra-light inline CSS + user theme
but adopt the decoration-pack motifs and `set:<name>` avatar rendering
(rounded-square crop; uploaded photos stay circle-cropped). Public pages stay
within the ~2 KB / no-tracker budget.
