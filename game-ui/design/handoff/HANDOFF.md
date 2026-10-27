# ITI AI Console — 3D HQ design handoff (for Gemini)

## What this is
`index.html` is a single-file, no-build design prototype of the **ITI AI Console** (Intellismart Technology Inc.'s
internal AI control center) shown as a Sims-4-style 3D headquarters (three.js r128 from cdnjs) plus an accessible
**List View** fallback. Open it directly in a browser. All data is fake/demo.

The real product: a FastAPI RAG service (answers only from uploaded company PDFs, with page citations and an
"I don't know" reply) plus tool calling into HRDotNet employee records, and a Next.js console (`admin-ui`).
This prototype is the "game-ui" second console design.

## Structure of index.html (search these headers)
- CSS 1 Brand tokens · 2 App shell / 3D viewport · 3 Floating HUD · 4 Shared controls · 5 List View · 6 Modals/toasts
- JS 1 `STATIONS` + `state` (demo data) · 2 toast/modal helpers + security-password gate
- JS 3 `SimsBuildCameraController` (Q/E orbit, R/F tilt, WASD pan, wheel zoom, Home reset)
- JS 4 Three.js world: wings, stations, Xia character (tap-to-move), app city blocks (3×5 / 3×3 offices,
  6 building archetypes), roads/traffic, PHT clock tower + real Asia/Manila solar lighting
- JS 5 Nav dock, hotspots, role enforcement · 6 HUD panels (11 pages) · 7 top controls + login modal
- JS 8 List View engine (`lvState`, `lvRender*`) · 8B themed `<select>` enhancer · 9 init on load

## Rules to keep (owner: Vince)
- **Colors only through CSS tokens** in `:root` / `html[data-theme=...]`. Dark = navy `#0A1128`, accent indigo
  `#6E76F0`; Light = cream `#F4F1EA` / paper `#FFFDF8`, accent gold `#9A6B12`. No raw hex in components
  (three.js material hexes are the exception; light mode must not show navy-blue surfaces).
- Font Comfortaa (rounded), mono for IDs/slugs/times. Floating cards with 16px gap, big radii, elevation tokens.
- Status is never color alone: dot/icon + word. Times are Asia/Manila (PHT).
- Accessibility target WCAG 2.2 AA: keyboard reachable hotspots, focus rings, reduced-motion support.
- Roles: super_admin (all), supervisor (no Admin wing: Accounts, Tools & MCP), tester (Chat only).
- Risky actions (keys, accounts, tools, MCP) go behind the security-password gate.
- No `alert/confirm/prompt`; use the modal + toast helpers.
- Never put real API keys, passwords or secrets in the file. Demo values only.

## Recent fixes already applied (keep them)
1. Typo `constledge.position.y` → `ledge.position.y` (archetype 1 buildings crashed `rebuildAppBuildings3D`).
2. `renderListViewApp()` only applies the theme in List View and only re-syncs the 3D scene when the theme changes.
3. `lvToggleTheme()` disables PHT auto-theme and syncs theme to the 3D view.
Verified: loads with no console errors; List View theme toggle carries back to 3D.

## Known rough edges / ideas
- `syncSceneThemeAndRoles()` calls `rebuildAppBuildings3D()` every time (heavy); could only rebuild on theme/app changes.
- 3D HUD data (`state`) and List View data (`lvState`) are two separate demo datasets with different names.
- Building pins hard-code "3×5 = 15 offices" text in the rename modal even for the 3×3 South block.

## How to work
Return the whole updated `index.html` (or exact find/replace blocks). Keep it one file, three.js r128 from cdnjs.
