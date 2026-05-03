# Lighthouse Frontend

The browser-side of the Lighthouse News Bias Report. A Next.js 14 app that
streams articles + a comparative bias report from the FastAPI backend and
renders them as side-by-side, color-coded analysis.

> Backend setup, environment variables, and ticket list live in the project
> [README](../README.md). Architecture diagrams are in
> [`docs/ARCHITECTURE_UML.md`](../docs/ARCHITECTURE_UML.md).

---

## Quick start

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

The dev server expects the backend on `http://localhost:8000`. Override with
`NEXT_PUBLIC_BACKEND_URL` in `.env.local` if needed.

| Command            | Purpose                                |
| ------------------ | -------------------------------------- |
| `npm run dev`      | Hot-reloading dev server               |
| `npm run build`    | Production build (also smoke-tests CI) |
| `npm start`        | Serve the production build             |
| `npm test`         | Run Vitest once                        |
| `npm run test:watch` | Vitest in watch mode                 |
| `npm run lint`     | Next.js ESLint pass                    |

> **Windows / PowerShell:** if `npm` is blocked by the execution policy, use
> `npm.cmd` or run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

---

## Stack

| Concern         | Choice                                                       |
| --------------- | ------------------------------------------------------------ |
| Framework       | Next.js 14 (App Router) + React 18                           |
| Styling         | Tailwind CSS with shadcn/ui-style CSS variables              |
| Components      | Radix primitives wrapped as shadcn/ui components             |
| Theming         | `next-themes` (light · dark · system) persisted to `localStorage` |
| Charts          | Recharts (sentiment) + bespoke SVG (bias spectrum)           |
| Map             | `react-simple-maps` + `world-atlas` TopoJSON                 |
| Icons           | `lucide-react`                                               |
| Tests           | Vitest + React Testing Library + jsdom                       |
| CI              | GitHub Actions — type-check, tests, build                    |

---

## Directory layout

```
frontend/
├── app/
│   ├── layout.tsx              ThemeProvider + TooltipProvider shell
│   ├── page.tsx                Home page — search + streaming results
│   ├── globals.css             Tailwind + light/dark CSS variables
│   └── api/health/             Edge health check
├── components/
│   ├── ui/                     shadcn-style primitives
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── badge.tsx
│   │   ├── separator.tsx
│   │   ├── progress.tsx
│   │   ├── tabs.tsx
│   │   └── tooltip.tsx
│   ├── theme-provider.tsx      next-themes wrapper
│   ├── theme-toggle.tsx        Sun/Moon button (persists to localStorage)
│   ├── SearchBar.tsx           Search input + suggestion chips
│   ├── ArticleCard.tsx         Per-article card with bias chips
│   ├── BiasReportPanel.tsx     Tabbed bias dashboard
│   ├── BiasSpectrum.tsx        NATO ↔ BRICS positioning chart
│   ├── SentimentChart.tsx      Recharts horizontal bar chart
│   └── RegionMap.tsx           Interactive world map (countries highlighted)
├── lib/
│   ├── streamClient.ts         SSE reader for /api/search
│   ├── utils.ts                cn() + countryFlag()
│   └── iso.ts                  ISO-2 → ISO-3166 numeric (for the map)
├── __tests__/                  Vitest specs
├── vitest.config.ts            jsdom + path alias
├── vitest.setup.ts             jest-dom matchers + Radix/Recharts shims
├── tailwind.config.ts          shadcn token mappings + bias colors
└── package.json
```

---

## What was shipped (frontend ticket list)

These map to the eight items in `lighthouse_frontend_tasks.md`.

### 1 · Polish to a hand-crafted standard

- Sticky header with logo, theme toggle, and About link.
- Hero section with a balanced display headline (Fraunces serif), an
  italic accent, and a status pill announcing the data sources.
- Skeleton loaders during streaming and a dedicated empty state.
- Footer with branding.
- Coherent spacing scale, typography, and a single accent color (amber)
  used sparingly for affordances.

### 2 · shadcn/ui as the component library

All UI primitives in [`components/ui/`](components/ui) are shadcn-style:
they use `class-variance-authority`, the `cn()` helper, and CSS variables
defined in [`app/globals.css`](app/globals.css). The Tailwind config in
[`tailwind.config.ts`](tailwind.config.ts) maps those variables onto Tailwind
color tokens (`bg-card`, `text-muted-foreground`, etc.) so every component
themes consistently in light *and* dark mode.

A custom `bias-*` color group is also exposed:

```ts
colors: {
  bias: {
    west:       'hsl(var(--bias-west))',
    brics:      'hsl(var(--bias-brics))',
    neutral:    'hsl(var(--bias-neutral))',
    government: 'hsl(var(--bias-government))',
    mixed:      'hsl(var(--bias-mixed))',
  },
}
```

### 3 · Interactive region map

[`components/RegionMap.tsx`](components/RegionMap.tsx). Built on
`react-simple-maps`. Article countries (ISO-2, e.g. `GB`, `CN`) are mapped
to ISO-3166 numeric ids via [`lib/iso.ts`](lib/iso.ts) and matched against
the `world-atlas@2/countries-110m.json` TopoJSON. Each highlighted country:

- Shades by article count (darker accent = more sources).
- Shows a Radix tooltip with the country name, article count, and the
  source list on hover.
- Is also listed in a flag/code/count chip strip below the map.

The component is dynamically imported with `ssr: false` from
[`app/page.tsx`](app/page.tsx) to avoid SSR issues.

### 4 · Clickable headlines

In [`components/ArticleCard.tsx`](components/ArticleCard.tsx) the headline
is an `<a>` with `target="_blank" rel="noopener noreferrer"`, an inline
`ExternalLink` glyph that fades in on hover, and a screen-reader hint
("opens in new tab"). Verified by an RTL test in
[`__tests__/ArticleCard.test.tsx`](__tests__/ArticleCard.test.tsx).

> **Note:** in mock mode the backend returns placeholder URLs
> (`https://bbc_news.example.com/...`). Real URLs require the backend
> tickets THE-8 and THE-9.

### 5 · Bias analysis redesign

Old plain-text panel replaced with a tabbed dashboard
([`components/BiasReportPanel.tsx`](components/BiasReportPanel.tsx)):

| Tab          | Contents                                                       |
| ------------ | -------------------------------------------------------------- |
| Summary      | Balanced summary + consensus-fact tiles                        |
| Spectrum     | [`BiasSpectrum`](components/BiasSpectrum.tsx) (positioned dots) + [`SentimentChart`](components/SentimentChart.tsx) (Recharts bar chart, −1 → +1) |
| Patterns     | Disputed framings + geopolitical pattern callouts              |
| Methodology  | Transparency note + per-search stat cards                      |

Per-card additions in [`ArticleCard`](components/ArticleCard.tsx):

- Color-coded left edge by bias direction
- Bias direction badge + confidence progress bar + sentiment chip
- Loaded-term pills + omissions list inside an animated disclosure

### 6 · Dark / light mode toggle

`next-themes` wired in [`components/theme-provider.tsx`](components/theme-provider.tsx)
from [`app/layout.tsx`](app/layout.tsx). The toggle in
[`components/theme-toggle.tsx`](components/theme-toggle.tsx) animates between
sun/moon icons; preference is persisted to `localStorage` under
`lighthouse-theme` and respects `prefers-color-scheme` on first visit.

### 7 · GitHub Actions for unit tests

[`.github/workflows/frontend-tests.yml`](../.github/workflows/frontend-tests.yml):

```yaml
on:
  push:    { branches: [main],  paths: [frontend/**, ...] }
  pull_request: { paths: [frontend/**, ...] }
jobs:
  test:
    steps:
      - actions/checkout@v4
      - actions/setup-node@v4 (node 20, npm cache)
      - npm ci
      - npx tsc --noEmit
      - npm test -- --reporter=verbose
      - npm run build           # smoke
```

Test setup:

- Vitest config in [`vitest.config.ts`](vitest.config.ts) (jsdom, alias `@/`)
- jest-dom matchers + Radix/Recharts globals shimmed in [`vitest.setup.ts`](vitest.setup.ts)
- 17 specs across 4 files in [`__tests__/`](__tests__):
  `SearchBar.test.tsx`, `ArticleCard.test.tsx`, `ThemeToggle.test.tsx`,
  `utils.test.ts`

### 8 · UML architecture diagram

[`docs/ARCHITECTURE_UML.md`](../docs/ARCHITECTURE_UML.md). Five Mermaid
diagrams that render natively on GitHub:

1. Component diagram — system topology (browser → FastAPI → external APIs)
2. Class diagram — domain model with cardinalities
3. Sequence diagram — full SSE streaming lifecycle of a single user query
4. Frontend component diagram — React tree + data sources
5. State machine — search lifecycle (`Idle → Streaming → Done | Error`)

---

## Theming model

CSS variables defined in [`app/globals.css`](app/globals.css) drive every
color. Dark mode flips them via the `.dark` class that `next-themes` toggles
on `<html>`.

```css
:root {
  --background: 40 33% 98%;
  --foreground: 220 25% 12%;
  --accent:     38 95% 52%;   /* warm amber — the "lighthouse" */
  --bias-west:  215 90% 55%;
  --bias-brics:   0 75% 55%;
  --bias-neutral: 145 55% 42%;
  ...
}
.dark { --background: 220 30% 7%; ... }
```

Tokens are consumed in components via Tailwind utilities (`bg-background`,
`text-bias-west`, etc.) — never raw `gray-*` / `slate-*` classes — so a
single variable change re-themes the whole app.

---

## Testing

```bash
npm test               # run once
npm run test:watch     # watch mode
```

The setup file ([`vitest.setup.ts`](vitest.setup.ts)) stubs `matchMedia`,
`ResizeObserver`, and `IntersectionObserver` because Radix and Recharts
both touch them and jsdom doesn't ship implementations.

Tests live next to the project root in [`__tests__/`](__tests__) and use the
`@/` alias just like production code.

---

## Where to extend next

- **Per-article comparison view.** The data is already there — group
  `articles` by topic cluster and render a 2-up diff alongside
  `BiasReportPanel`.
- **Source filter chips.** A row above the article grid that filters by
  alliance bloc / country, all client-side over the streamed bundle.
- **Real article URLs.** Implement backend tickets THE-8 and THE-9 — no
  frontend changes needed; the headlines are already real `<a>` tags.
