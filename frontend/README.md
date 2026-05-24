# Canon Frontend

Observation and management layer for Canon — organizational memory for engineering teams.

## Tech Stack

- **Next.js 16** (App Router)
- **TypeScript** (strict mode)
- **Tailwind CSS v4** with custom theme
- **react-force-graph-2d** for memory graph visualization

## Getting Started

```bash
pnpm install
cp .env.local.example .env.local  # edit API_URL to point to your backend
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment Variables

| Variable              | Purpose                                          |
| --------------------- | ------------------------------------------------ |
| `API_URL`             | Backend REST API URL (server-side only)          |
| `NEXT_PUBLIC_API_URL` | Backend URL for MCP config display (client-side) |

## Architecture

- **Server Actions** (`lib/actions/`) — all backend communication, Zod-validated
- **Route Handler** (`api/stream/[sessionId]`) — Edge Runtime SSE proxy
- **Middleware** (`middleware.ts`) — JWT cookie auth + onboarding redirect
- **Styled** with Tailwind v4 `@theme` variables (canon-\* namespace)
