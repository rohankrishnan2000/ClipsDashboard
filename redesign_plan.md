# Klipo → Vercel/Geist Re-skin — Implementation Spec

## Goal
Re-skin the EXISTING functional clipping-bot frontend (`frontend/src`) so it visually matches the
**Vercel dashboard (Geist design system)** shown in `Screenshot 2026-06-22 at 10.14.14 PM.png`.
The screenshot is the **gold standard** for fonts, text size, spacing, color, borders, bars, buttons,
and images. The **left sidebar must be a near-exact match** to Vercel's.

Hard rules:
- Do NOT remove or break existing functionality. Every button/input that exists today must keep working
  against the backend (search VODs, start job, poll progress, view/download clips, tabs, page nav).
- Do NOT invent frontend features that have no backend (the evaluator will fail you for this). Keep the
  app's REAL pages/nav (Dashboard, Find VODs, Clips, Jobs, Analytics, Settings, Help) — just style them
  exactly like Vercel's sidebar. No "Deployments/Domains/CDN" dead links.
- This is purely a visual/CSS + light markup re-skin. Backend untouched.

## Target design system (from the pasted Geist CSS + screenshot)

### Font
- Load **Geist** + **Geist Mono** via Google Fonts in `frontend/index.html`:
  `https://fonts.googleapis.com/css2?family=Geist:wght@300..700&family=Geist+Mono:wght@400..600&display=swap`
- `--font: "Geist", -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;`
- Mono (for usage numbers/metrics if used): `"Geist Mono", ui-monospace, monospace;`

### Color tokens (light theme — replace the green/warm palette entirely)
```
--bg:            #ffffff      /* main app background */
--bg-200:        #fafafa      /* subtle panel/canvas fills, ds-background-200 */
--surface:       #ffffff
--gray-100:      #f2f2f2      /* hover/active row fill */
--gray-200:      #ebebeb      /* borders (ds-gray-200) */
--gray-300:      #e5e5e5
--gray-alpha-100:rgba(0,0,0,.05)
--gray-alpha-200:rgba(0,0,0,.08)
--ink:           #171717      /* primary text, ds-gray-1000 */
--ink-2:         #666666      /* secondary text/icons, ds-gray-900/800 */
--ink-3:         #8f8f8f      /* tertiary/placeholder, ds-gray-700 */
--blue:          #0070f3      /* ds-blue link/accent */
--blue-700:      #0070f3
--amber:         #f5a623      /* badges like "beta" if needed */
--success:       #0070f3
--btn-dark:      #000000      /* "Add New..." style primary button bg */
--radius:        6px          /* geist-radius */
--radius-sm:     4px
```
- Shadows: extremely subtle. Cards/panels use **1px solid var(--gray-200) borders**, NOT big drop
  shadows. Vercel is flat/bordered. (e.g. `border:1px solid var(--gray-200); border-radius:8px;`)

### Layout shell
- Sidebar fixed **256px** wide (`--sidebar-width`), white, separated from content by a **1px right border**
  (`border-right:1px solid var(--gray-200)`), NOT a floating rounded card. No outer page padding/gap —
  sidebar is flush to the left edge, content fills the rest. Full viewport height.
- Main column: white background. A top bar (~56px, `--navbar-height`) with a 1px bottom border, then the
  scrollable content area with generous padding (~24px).

### Sidebar (PRIORITY — match the screenshot closely)
Top → bottom:
1. **Account/org switcher row** at very top: small ~22px rounded avatar square + name ("Rohan K." is fine)
   in ~14px **medium (500)** `--ink`, a small **"Hobby"** plan pill in `--ink-2` to the right, and an
   up/down chevron at far right. Whole row is a button with subtle hover (`--gray-100`).
2. **Search field** "Find..." — full width, `--bg-200` fill, 1px `--gray-200` border, 6px radius, ~32px tall,
   13–14px placeholder in `--ink-3`, small search icon left, optional faint `⌘K`-style hint on the right.
3. **Flat nav list** (no big uppercase section labels like the current "MENU/PREFERENCE"). Each row:
   - height ~32px, padding ~6px 8px, gap ~10px, border-radius 6px
   - 16px lucide icon, stroke ~1.75, color `--ink-2`
   - label 14px, weight 400, color `--ink-2`
   - **hover**: background `--gray-100`, text `--ink`
   - **active**: background `--gray-100` (or alpha-100), text `--ink`, weight 500. (Vercel's active row is a
     subtle gray fill, NOT a colored left-bar — remove the green accent bar.)
   - tight vertical rhythm (~2px gap between rows)
   - Keep the app's real items: Dashboard, Find VODs, Clips, Jobs, Analytics, then Settings, Help Center.
     A thin divider or small gap may separate the main group from Settings/Help (mirrors Vercel grouping)
     but do NOT add loud uppercase group headers.
   - The Jobs running-count badge: render as a small gray/numeric pill on the right (Vercel-style), not green.
4. Push to bottom: **user account row** (avatar + truncated email "rohankrishnan000…") as a button with
   hover, mirroring the top row. (Replaces the green "Raw cuts" promo card — drop that card; it doesn't
   exist in the gold standard.)

### Top bar (main area)
- Keep the existing search/assistant/notifications/profile functionality but restyle to Geist:
  - Background white, 1px bottom border, height ~56px, horizontal padding ~24px.
  - Search input: flat, `--bg-200` fill, 1px border, 6px radius, search icon, `⌘K` hint.
  - Replace the bright green "Assistant" pill with a neutral/secondary button (white bg, 1px border, dark
    text) OR a subtle blue link — no neon green.
  - Notification icon button: ghost, gray icon, square ~32px, 6px radius, subtle hover; keep the unread dot
    but recolor to `--blue` or red, not orange.
  - Profile: avatar (rounded 6px, ~28–32px) + name/role text in Geist sizes; chevron.

### Buttons (global)
- **Primary** (`.btn-accent` today): black background (`--btn-dark`), white text, 6px radius, 13–14px,
  weight 500, ~32–36px tall, padding ~8px 14px, subtle hover (slightly lighter black / `#333`). This
  matches Vercel's black "Add New…"/"Deploy" primaries. Remove green + glow box-shadows.
- **Secondary/ghost**: white bg, 1px `--gray-200` border, `--ink` text, hover `--bg-200`.
- Disabled: reduced opacity, no transform.
- Remove the lime/glow shadows everywhere.

### Panels / cards
- White, **1px solid `--gray-200` border**, 8–10px radius, minimal/no shadow. Section headers in 14–16px
  weight 500/600 `--ink`, supporting text 13px `--ink-2`. Generous internal padding (~16–20px).
- Stat cards, tabs, tables, clip cards, job progress, empty states: re-skin to the same bordered-flat,
  near-monochrome Geist look. Tabs: underline or subtle pill in gray, active = `--ink` text (no green pill).
- Progress bar: track `--gray-200`, fill `--ink` or `--blue` (not green gradient).
- Badges: neutral gray by default; use `--blue`/red sparingly. The clip "score" pill → neutral or blue,
  not lime.

### Typography scale (approx, match screenshot)
- Page H1: ~24px weight 600, letter-spacing -0.02em, `--ink`.
- Panel title: ~15–16px weight 600.
- Body/labels: 13–14px.
- Muted/meta: 12–13px `--ink-2`/`--ink-3`.
- Use Geist's tighter, neutral feel — avoid the current 800-weight chunky headings.

## Files to edit
- `frontend/index.html` — add Geist font links, set title.
- `frontend/src/styles.css` — the bulk of the work: replace tokens + every component block.
- `frontend/src/components/AppSidebar.tsx` — restructure to account-row + search + flat nav + bottom
  account row; drop promo card; keep `PageKey`/nav wiring intact.
- `frontend/src/components/TopBar.tsx` — restyle (read it first).
- Touch `StatCard.tsx`, `VodTable.tsx`, `ClipCard.tsx`, `JobProgress.tsx`, `PlaceholderPage.tsx`,
  `DashboardPage.tsx`, `JobsPage.tsx` only as needed for markup/className changes; keep all logic/handlers.

## Verification (MANDATORY — screenshot rule)
Dev servers are already running: frontend **http://localhost:5174**, backend on :8000.
A screenshot helper exists:
`node /private/tmp/claude-501/-Users-rohankrishnan-Coding-clipping-bot/50d52593-ada8-42cd-85f9-8e34a90db110/scratchpad/shot.mjs <url> <out.png> 1440x900`
The gold-standard image is `/Users/rohankrishnan/Coding/clipping_bot/Screenshot 2026-06-22 at 10.14.14 PM.png`.

Loop until it matches:
1. Make changes.
2. Screenshot the dashboard, jobs page, and a placeholder page.
3. Open BOTH your screenshot and the gold standard and compare sidebar font/size/spacing/color, borders,
   buttons, overall light theme. Fix discrepancies. Repeat.
4. Pay special attention: sidebar must look like the screenshot's sidebar (flat nav, gray active row,
   account rows top+bottom, search field), and the whole app must be the light bordered Geist look with
   NO leftover green/lime/warm-gray.
5. Confirm `npm run build` (`tsc -b && vite build`) passes with no type errors.
6. Confirm interactive flows still work (search a username, the controls render, tabs switch).
