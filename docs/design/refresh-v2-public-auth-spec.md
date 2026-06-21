> Canonical reference for the **v0.5.0** cycle (public profile + auth screens; issues #50–#56). Delivered as React/Babel prototypes — reference only; rebuild in Flask/Jinja + vanilla CSS per RULES.md. The prototype files and tweaks panel are intentionally not committed.
# Handoff: cutecumber — Public Profile pages & Auth screens

## Overview
Second design package for **cutecumber.cc**, covering the two surfaces left after the landing + dashboard work (see `design_handoff_landing_dashboard/`):
1. **Public profile page** — `cutecumber.cc/<username>`, the page a creator shares. Phone-first, themeable (6 presets incl. dark), with two layout shapes (centered + wide/desktop) and an **opt-in animated ambient background** tied to the user's decoration pack.
2. **Auth & state screens** — `log in`, `sign up`, **claim username** (first-run), **check your email** (magic-link sent), **username taken** (claim error), and **404** (page not found). All reuse the landing shell (slice wordmark + soft card + ambient).

Shares the brand system from the earlier phases (`Design Spec.html`, `production/` SVGs).

## About the Design Files
The bundled files are **design references built in HTML + React/Babel** — they show intended look, motion, and behavior; **they are not production code to ship verbatim.** The live app is **Flask + Jinja + vanilla JS/CSS**, with hard constraints: no trackers/cookies, tiny payloads (public pages target **~2 KB**), WCAG-AA contrast.

**Task: recreate these in the Flask/Jinja codebase using its existing patterns.**
- Public page → `app/templates/public_page.html` (it carries its **own tiny inline CSS** — keep it that way; do **not** pull in `dash.css`).
- Auth/state screens → their existing templates/routes (`auth.login`, `auth.signup`, `dash.claim`, plus new check-email / taken / 404 states), reusing the landing shell styles.
- **Do not introduce React.** Translate components to Jinja + minimal vanilla JS. The ambient background → a small **static inline SVG layer**, CSS-animated, `aria-hidden`, `pointer-events:none`, behind a `z-index:1` content layer. `tweaks-panel.jsx` is a **design tool only — ignore for production.**

## Fidelity
**High-fidelity.** Exact tokens, layout, copy, and motion below.

---

## Design Tokens

### Shared UI tokens (same as package 1)
green `#3f5a39` · ink `#3c3c43` · muted `#6e6e78` · faint `#8a8a93` · accent `#e58fb1` · accent-deep `#d97da2` (or `color-mix(in oklab, var(--accent) 80%, #5b2c41)`) · border `#f0d4de` · page gradient `linear-gradient(160deg,#fff5f7,#f3f9f4)`. Fredoka 600 lowercase for display/wordmark/headings; `system-ui` for body. Pills `border-radius:999px`; cards `20–24px`. Brand-art palette (motifs/avatars): body `#8fcb72`, bodyDark `#6da854`, bodyLight `#a9da8d`, flesh `#ecf7df`, seed `#cde8b4`, face-ink `#33502e`, blush `#f7b1c8`.

### Public-page theme presets (the user's chosen theme drives the page)
Each preset sets `--bg, --bg2, --text, --muted, --accent, --accent-text, --card-line`. Values (mirror `theme.py` PRESETS; all AA on their own bg):

| preset | bg | bg2 | text | muted | accent | accent-text | dark |
|---|---|---|---|---|---|---|---|
| strawberry_milk | `#fff5f7` | `#ffe2ee` | `#53343f` | `#80666f` | `#e58fb1` | `#26171d` | – |
| matcha_latte | `#f4f9ef` | `#e3efd6` | `#2f3d28` | `#5b6a51` | `#5f8a4d` | `#ffffff` | – |
| lavender_haze | `#f7f3fd` | `#e7d9fb` | `#382f4a` | `#665b7c` | `#7a59c8` | `#ffffff` | – |
| cherry_cola | `#fdf1ef` | `#f6d6d0` | `#4a2730` | `#7c545d` | `#b23350` | `#ffffff` | – |
| seafoam | `#eefaf6` | `#d2efe7` | `#1f3d39` | `#4c6863` | `#1f7d76` | `#ffffff` | – |
| midnight_snack | `#2d2d49` | `#232338` | `#f1edf9` | `#bbb9c7` | `#f3a7c3` | `#26171d` | ✓ |

Link buttons fill with `--accent` / text `--accent-text`, `box-shadow: 0 6px 18px color-mix(in oklab, var(--accent) 38%, transparent)`; hover lifts `translateY(-2px)`. Avatar ring uses `--card-line` for its 4px ring.

### Radius / shadow specifics
public avatar ring `50%` (104px mobile / 128px wide) + `box-shadow: 0 8px 22px rgba(40,30,40,.16), 0 0 0 4px var(--card-line)`; link buttons `999px`; auth card `24px` + `0 14px 40px rgba(229,143,177,.18)`; auth field box `13px`, focus `border accent + 0 0 0 3px rgba(229,143,177,.22)`.

---

## Screens / Views

### A. Public profile page (`/<username>`)
**Purpose:** a visitor reads who this is and taps a link. **Phone is the primary target.**

**Default = centered, phone-first.** Single column, `max-width:460px`, centered, padding `56px 20px 40px`:
- **Avatar** — circle, 104px, object-fit cover, ring shadow. **All avatars are circle-cropped** (set-avatars and uploaded photos alike — one shape, per decision).
- **Name** (Fredoka, `--text`, 1.8rem), **pronouns** (muted .92rem), **bio** (1rem, `max-width:34ch`, `text-wrap:pretty`).
- **Links** — `display:grid; gap:13px`. Each `.linkbtn`: full-width pill, `padding:16px 44px`, accent fill, centered label, optional emoji **absolutely positioned left** (`left:18px`) so labels stay optically centered; hover lift. 
- **Footer credit** — toggleable: either "🥒 made with cutecumber" (slice mark 15px + muted link) or a minimal "report" link when the user turns the credit off. (Maps to a per-user `show_credit` boolean.)

**Wide / desktop-aware layout** (≥ 860px, user-selectable): centered `max-width:920px`, `grid-template-columns:340px 1fr; gap:56px`. Left = **sticky** profile (`top:64px`), left-aligned, avatar 128px, name 2.2rem. Right = links as a **single full-width column** (`gap:12px`), left-aligned (`padding-left:52px`, emoji at `left:20px`), so long titles sit on one line. *(Important: an earlier 2-column grid caused long titles to wrap/cut off — keep links one column in wide.)* Credit spans full width, left-aligned.

**Ambient background (opt-in theme option, default OFF in production):** animated drifting pack motifs hugging the margins + a big faint slice watermark. Motifs are chosen from the user's **decoration pack** (`garden_patch`, `sakura_dreams`, `cozy_cafe`, `little_friends` → motif lists in `public.jsx` `PACK_MOTIFS`); placement/size/opacity/timing in `public.jsx` `SPOTS`. On dark themes the motif drop-shadow deepens (`.is-dark`). **Phone rule:** hide motifs beyond the first ~7 (`@media (max-width:600px){ .motif:nth-child(n+8){display:none} }`) and drop watermark opacity — protects small screens and payload. Motion gated behind `prefers-reduced-motion: no-preference`.

**Responsive:** centered is the mobile baseline; wide only engages ≥860px when selected. Keep tap targets ≥44px (link pills are ~52px tall).

### B. Auth & state screens
All share the **shell**: full-viewport gradient, optional ambient (landing-style, count ~8), a centered column `max-width:400px`, the **slice wordmark** centered above (slice 42px + "cutecumber" Fredoka green 1.6rem), then one **card** (`rgba(255,255,255,.92)`, blur 10, radius 24, padding `30px 26px`, soft shadow). *(The pill switcher at the top of the prototype is **prototype-only** navigation — each screen is its own route/state in production.)*

1. **Log in** — H1 "welcome back 🌱", sub "log in to tend your page.". Form: **email** field (default) with a text-button toggle **"use username instead"** (swaps label/placeholder; username variant shows the `cutecumber.cc/` prefix); **password** field with a **show/hide** reveal button; primary **log in**. `—or—` divider. Ghost button **"email me a magic link ✨"**. Foot: "new here? claim your username". 
   **→ For implementation: enable all three sign-in methods** — (1) email + password [default], (2) username + password [via the toggle], (3) magic link [passwordless email]. Default the UI to email+password; expose the other two as shown.
2. **Sign up** — H1 "claim your cutecumber 🥒", sub "one tiny page for all your links. free, forever.". email + password (show/hide) + primary "create my account ✨"; `—or—`; ghost "sign up with a magic link 💌"; foot "already have one? log in".
3. **Claim username** (first-run) — H1 "pick your username 🌱", sub about permanence. Prefix field `cutecumber.cc/ [input]`; **live availability line** below (`.avail.ok` green check / `.avail.bad` muted prompt) validating the pattern `^[a-z0-9][a-z0-9_-]{1,28}[a-z0-9]$`; primary **claim it ✨** (disabled until valid); hint on allowed chars. Lowercases input on type.
4. **Check your email** (magic-link sent) — centered card: slice mark 64px with a small pink sparkle badge; H1 "check your inbox 💌"; sub "we sent a magic link to **{email}** — tap it and you're in. it expires in 15 minutes."; ghost **resend the link**; foot "use a different email".
5. **Username taken** (claim error) — same claim layout but field has `.is-error` (red border `#e7a6b3`), `.avail.err` line "🥺 cutecumber.cc/{name} is already taken", and a **suggestions** block: label "how about…" + a row of **chips** (`.chip`: white pill, 2px border, accent-deep text, hover bg `#fff5f7`) offering alternates (e.g. `{name}_draws`, `{name}makes`, `hello{name}`, `{name}-art`).
6. **404 — page not found** — centered card: slice mark 76px with an accent **?** badge; H1 "this patch is empty 🌱"; sub "there's no page at **cutecumber.cc/{name}** yet — the name might be free!"; primary **claim this username ✨**; foot "← back to cutecumber". (Turns a dead URL into a signup funnel.)

---

## Interactions & Behavior
- **Public links** → open the saved URL (new tab as today); hover lift `translateY(-2px)` + deeper shadow, 0.12s.
- **Login method toggle** → swaps email ⇄ username field (label, type, prefix). **Show/hide** → toggles password input type. Keep no-JS fallback (default email+password posts fine without JS).
- **Claim validation** → client-side regex for instant feedback; server still authoritative (returns the **taken** state on collision). Disable submit while invalid.
- **Suggestion chips** → clicking one fills the username field and re-checks.
- **Resend / different email** (check-email) → resend POST / return to login.
- **Motion** → ambient `drift` (float −24px + rotate +6°, 8–17s staggered) and `bob` (watermark, 22s); both **only** under `@media (prefers-reduced-motion: no-preference)`. Default on; print/reduced-motion show static.

## State Management
- **Public page:** read-only render from the user's profile + theme + links + `decoration` pack + `show_credit` flag. Theme tokens come from `theme.py`; layout shape (`centered`/`wide`) and ambient on/off are **user theme settings** to add (booleans/enums) — default centered, ambient off.
- **Auth:** login = `{identifier (email|username), password}` or magic-link `{email}`; signup = `{email, password}` or magic-link; claim = `{username}` with live-valid boolean; check-email = `{email}` display; taken = `{attempted, suggestions[]}`; 404 = `{attempted_name}`.
- Sign-in **method** is a small UI state (email/username/magic) — default email+password.

## Design Tokens (additional)
Error: field border `#e7a6b3`, focus `#d4566a` + `rgba(212,86,106,.18)`; avail-ok green `#1c6b3c`; avail-err `#a33a52`. Chip border `var(--border)`, text `var(--accent-deep)`. 404 badge bg `var(--accent)`, text `#fff`.

## Assets
- `production/brand/logo_slice.svg` — slice mark (wordmark, auth marks, watermark, favicon).
- `production/avatars/*.svg` — avatar set; `bun.svg` used in the public example. Render **circle-cropped** on public pages.
- Motifs — inline SVG in `motifs.jsx` (`MOTIF` map); pack→motif mapping in `public.jsx` (`PACK_MOTIFS`). Port to a static SVG sprite for production.
- Font: `app/static/fonts/fredoka-latin-600-normal.woff2`.

## Files in this bundle
- `Public Profile Page.html` — public page prototype (Tweaks: layout, theme, ambient, pack, motion, credit).
- `Auth Screens.html` — all six auth/state screens (top switcher to flip).
- `public.jsx` — themes (`THEMES`), pack motifs (`PACK_MOTIFS`), ambient placement (`SPOTS`), profile/links/credit components.
- `auth.jsx` — the six screen components + field helper.
- `motifs.jsx` — shared brand SVG set + ambient + slice mark.
- `tweaks-panel.jsx` — **design tool only; do not ship.**
- `production/` — brand mark + avatar SVGs.
- Targets to edit: `app/templates/public_page.html`, the auth templates/routes, and a shared landing-shell partial.
