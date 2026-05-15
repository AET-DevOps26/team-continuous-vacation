# TripTailor Frontend

React 19 + Vite + [Refine](https://refine.dev) application with shadcn/ui components and Tailwind CSS.

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
│   ├── login/index.tsx    # Login page with demo session button
│   └── trips/
│       ├── list.tsx       # Trip dashboard (card grid, delete)
│       ├── create.tsx     # Trip generation form (destination, dates, vibe)
│       └── show.tsx       # Visual schedule view with activity regeneration
├── components/
│   ├── ui/                # shadcn/ui primitives (button, card, input, etc.)
│   └── refine-ui/         # Refine layout, notifications, theme
├── test/                  # Vitest setup and test utilities
└── App.tsx                # Root with routing and Authenticated guards
```

## How It Was Built

1. **Type generation**: `openapi-typescript` generates `api-types.ts` from `api-specification/frontend.yaml`
2. **API client**: `openapi-fetch` provides a fully typed HTTP client — requests and responses are validated against the OpenAPI schema at compile time
3. **Refine framework**: Provides data-fetching hooks (`useList`, `useShow`, `useCreate`, `useUpdate`, `useDelete`), auth guards, routing, and notifications out of the box
4. **UI**: shadcn/ui components (Radix primitives + Tailwind CSS)

## Commands

```bash
npm install --legacy-peer-deps    # Install dependencies
npm run dev                       # Start dev server (Vite on port 5173)
npm run build                     # TypeScript check + production build
npm run lint                      # ESLint
npm run test                      # Vitest (unit + component tests)
npm run generate-api-types        # Regenerate types from OpenAPI spec
```

## Environment Variables

| Variable       | Default                  | Description                  |
|----------------|--------------------------|------------------------------|
| `VITE_API_URL` | `http://localhost:8080`  | Backend API base URL         |

## Docker

```bash
docker build -t triptailor-frontend .
docker run -p 3000:3000 triptailor-frontend
```

The Dockerfile uses a multi-stage build (node:20-alpine) to compile and then serves the SPA with `serve`.

## Testing

Tests use **Vitest** + **React Testing Library** + **jsdom**. Test files are co-located with source (`*.test.ts` / `*.test.tsx`) and excluded from the production TypeScript compilation.

```bash
npm run test          # Single run
npm run test:watch    # Watch mode
```
