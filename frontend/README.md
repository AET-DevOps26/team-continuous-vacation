# TripTailor Frontend

React 19 + Vite + [Refine](https://refine.dev) application with shadcn/ui components and Tailwind CSS 4.

## Architecture

```
src/
├── lib/
│   ├── api-types.ts       # Auto-generated TypeScript types from OpenAPI spec
│   ├── api-client.ts      # openapi-fetch client with bearer token middleware
│   └── utils.ts           # Tailwind merge utility
├── providers/
│   ├── auth-provider.ts   # Refine AuthProvider (login, register, demo session)
│   └── data-provider.ts   # Refine DataProvider mapped to /trips & /activities API
├── pages/
│   ├── login/index.tsx    # Auth page (login, register, demo) with mode toggle
│   └── trips/
│       ├── list.tsx       # Trip dashboard (responsive card grid, delete)
│       ├── create.tsx     # Trip generation form (destination, dates, vibe picker)
│       └── show.tsx       # Visual schedule with time-block colors, activity regeneration & delete
├── components/
│   ├── ui/                # shadcn/ui primitives (button, card, input, sidebar, etc.)
│   └── refine-ui/         # Layout (sidebar, header, theme toggle, user dropdown)
├── test/                  # Vitest setup and test utilities
└── App.tsx                # Root with BrowserRouter, Authenticated guards, route config
```

## API Coverage

All endpoints from `api-specification/frontend.yaml` are implemented:

| Endpoint | Method | Usage |
|----------|--------|-------|
| `/auth/register` | POST | Register form on login page |
| `/auth/login` | POST | Login form on login page |
| `/auth/demo` | POST | "Try Demo" button on login page |
| `/trips` | GET | Trip list page |
| `/trips` | POST | Trip creation form |
| `/trips/{tripId}` | GET | Trip detail/schedule page |
| `/trips/{tripId}` | DELETE | Delete button on trip cards |
| `/trips/{tripId}/days/{dayId}/activities/{activityId}` | PATCH | Regenerate activity with instruction |
| `/trips/{tripId}/days/{dayId}/activities/{activityId}` | DELETE | Delete activity button |

## Commands

```bash
npm install --legacy-peer-deps    # Install dependencies
npm run dev                       # Start dev server (Vite on port 5173)
npm run build                     # TypeScript check + production build
npm run lint                      # ESLint
npm run test                      # Vitest (unit + component tests)
npm run test:watch                # Vitest in watch mode
npm run generate-api-types        # Regenerate types from OpenAPI spec
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `""` (empty, uses relative paths) | Backend API base URL |

In development, Vite proxies `/auth`, `/trips`, and `/health` to `http://localhost:8080`.

## Docker

```bash
docker build -t triptailor-frontend .
docker run -p 3000:3000 triptailor-frontend
```

Multi-stage build: `node:20-alpine` compiles the SPA, then `serve` serves static files on port 3000. Pass `--build-arg VITE_API_URL=...` to set the API URL at build time.

## Testing

Tests use **Vitest** + **React Testing Library** + **jsdom**.

Test files are co-located with source (`*.test.ts` / `*.test.tsx`) and excluded from production TypeScript compilation via `tsconfig.json`.

```bash
npm run test          # Single run (used in CI)
npm run test:watch    # Watch mode for development
```

## Design

- **Color palette**: Slate-blue tinted (oklch hue 260) with indigo primary. Clean in both light and dark modes.
- **Activity cards**: Time-block coloring (amber/sky/orange/violet/slate) with good contrast in both themes.
- **Layout**: Full-width content with collapsible sidebar. Sidebar can be reopened via header trigger.
- **Responsive**: Grids adapt from 1 to 5 columns depending on viewport width.
