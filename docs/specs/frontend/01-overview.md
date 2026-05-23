# 01 — Frontend Overview

## Purpose

The Canon frontend is a lightweight observation and management layer. Engineers
use it to see Canon's reasoning in real time (the Reasoning Feed), browse
session history, explore the organizational memory graph, and manage team
membership. It is not the primary interface to Canon — the coding harness is.
The frontend makes the system legible.

---

## Tech Stack

| Layer      | Choice                  | Rationale                                         |
| ---------- | ----------------------- | ------------------------------------------------- |
| Framework  | Next.js 15 (App Router) | Server components, API routes, Vercel-native      |
| Deployment | Vercel                  | Zero-config Next.js deployment                    |
| Styling    | Tailwind CSS            | Functional defaults, polish pass later            |
| Graph Viz  | react-force-graph-2d    | D3-force with React wrapper, good for <1000 nodes |

---

## Architecture

### Frontend ↔ Backend Only

The frontend has **no direct database connection**. It does not know about
MongoDB. All data flows through the Cloud Run backend's REST API.

```
Coding Harness (Cursor, Claude Code)
    │
    │ MCP over HTTP (api_token auth)
    ▼
Backend (Cloud Run) ◄────── REST API (JWT auth) ────── Frontend (Vercel)
    │
    ▼
MongoDB Atlas
```

The backend is the single source of truth. It exposes two authentication
surfaces:

| Surface       | Auth Mechanism     | Consumer       |
| ------------- | ------------------ | -------------- |
| MCP endpoints | API token (Bearer) | Coding harness |
| REST API      | JWT (Bearer)       | Frontend       |

### Implications

- The backend owns all collections — including `users` and `invites` (added for
  frontend auth/onboarding).
- The frontend stores no secrets except the JWT in an httpOnly cookie.
- Components never call `fetch` directly. All backend communication goes through
  **Next.js server actions** (`"use server"` functions in `lib/actions/`).
  Server actions run on the Next.js server, keeping the JWT cookie httpOnly and
  the `API_URL` out of client bundles.
- Backend API routes are documented in Backend Doc 04 (extended for frontend).

---

## Routing

| Route                   | Page               | Auth Required |
| ----------------------- | ------------------ | ------------- |
| `/`                     | Landing / redirect | No            |
| `/login`                | Login              | No            |
| `/register`             | Register           | No            |
| `/onboarding`           | Create/join team   | Yes           |
| `/dashboard`            | Session list       | Yes           |
| `/sessions/[sessionId]` | Session detail     | Yes           |
| `/graph`                | Memory graph       | Yes           |

### Middleware

Next.js middleware protects authenticated routes. Unauthenticated users are
redirected to `/login`. Users without a tenant association are redirected to
`/onboarding`.

Auth state is determined by the presence and validity of a JWT stored in an
httpOnly cookie. The JWT is issued by the backend's `/api/v1/auth/login`
endpoint.

---

## Backend API Surface

The frontend consumes these backend REST API routes. All authenticated routes
require `Authorization: Bearer <jwt>`.

### Auth

| Route                   | Method | Purpose                                |
| ----------------------- | ------ | -------------------------------------- |
| `/api/v1/auth/register` | POST   | Create account (email, name, password) |
| `/api/v1/auth/login`    | POST   | Login → returns JWT                    |
| `/api/v1/auth/me`       | GET    | Current user profile + tenant info     |

### Teams

| Route                  | Method | Purpose                           |
| ---------------------- | ------ | --------------------------------- |
| `/api/v1/teams/create` | POST   | Create team + tenant              |
| `/api/v1/teams/join`   | POST   | Join team via invite code         |
| `/api/v1/teams/invite` | POST   | Generate invite code (owner only) |
| `/api/v1/teams/tokens` | GET    | List harness API tokens           |
| `/api/v1/teams/tokens` | POST   | Create harness API token          |

### Sessions & Events

| Route                                  | Method | Purpose          |
| -------------------------------------- | ------ | ---------------- |
| `/api/v1/sessions`                     | GET    | List sessions    |
| `/api/v1/sessions/{session_id}`        | GET    | Session detail   |
| `/api/v1/sessions/{session_id}/events` | GET    | Session events   |
| `/api/v1/sessions/{session_id}/stream` | GET    | SSE event stream |

### Graph

| Route           | Method | Purpose                      |
| --------------- | ------ | ---------------------------- |
| `/api/v1/graph` | GET    | Memory nodes + edges for viz |

---

## Environment Variables

```
API_URL=https://canon-<project>.run.app
```

Server-only environment variable (no `NEXT_PUBLIC_` prefix). Only server actions
need to reach the backend — the client never calls the backend directly.

---

## Tenant Scoping

Every data request is scoped to the user's tenant. The JWT contains the user's
`tenantId` — the backend extracts it from the JWT claim and filters all queries
accordingly. No user can access another tenant's data.

---

## Data Access Pattern — Server Actions

All backend communication goes through Next.js server actions. Components never
call `fetch` directly.

```
lib/actions/
├── auth.ts       # login, register
├── teams.ts      # createTeam, joinTeam, createInvite, listTokens, createToken
├── sessions.ts   # listSessions, getSession, getSessionEvents
└── graph.ts      # getGraph
```

Each action file is `"use server"` and contains typed, Zod-validated functions.
Tenant scoping is handled by the backend via JWT — actions don't need a
`tenantId` parameter:

```typescript
// lib/actions/sessions.ts
"use server";

import { z } from "zod";
import { cookies } from "next/headers";

const API_URL = process.env.API_URL!;

const SessionSchema = z.object({
  sessionId: z.string(),
  title: z.string().nullable(),
  summary: z.string().nullable(),
  status: z.string(),
  runCount: z.number(),
  lastRunAt: z.string(),
  createdAt: z.string(),
});

const SessionListSchema = z.array(SessionSchema);

export async function listSessions() {
  const token = (await cookies()).get("canon_token")?.value;
  const res = await fetch(`${API_URL}/api/v1/sessions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return SessionListSchema.parse(await res.json());
}
```

**Why server actions over raw fetch?**

- JWT stays in httpOnly cookie — never exposed to client JS
- `API_URL` is server-only — not leaked in client bundles
- Zod validation at the action boundary — components receive typed data
- Single place to handle auth errors (redirect to `/login` on 401)

**Exception**: SSE streams can't use server actions (they're request-response).
Instead, a Next.js **Route Handler** (`app/api/stream/[sessionId]/route.ts`)
running on the **Edge Runtime** proxies the backend SSE stream. The browser
connects to `/api/stream/{sessionId}` on the Next.js server, which forwards the
JWT cookie as a Bearer token — keeping `API_URL` server-side. Edge Runtime's
300s limit is sufficient for Canon runs (seconds to a minute each). The client
includes auto-reconnection with sequence-based resume as a safety net. See
Frontend Doc 03 for implementation.

---

## Code Quality Guidelines

- **Zod everywhere.** Validate all API responses at the boundary with Zod
  schemas. Define shared schema files (`lib/schemas/`) that match the backend
  contracts. Parse, don't assume.
- **No `any`.** TypeScript strict mode. Infer types from Zod schemas
  (`z.infer<typeof schema>`).
- **Small, focused components.** One responsibility per component. Extract hooks
  for data fetching and state management.
- **Colocation.** Keep component-specific types, hooks, and utilities next to
  the component that uses them. Shared utilities go in `lib/`.
- **No dead code.** Remove unused imports, variables, and components
  immediately.
- **Error handling at boundaries only.** API calls get try/catch. Internal
  functions trust their inputs (validated upstream by Zod).
- **Consistent naming.** `camelCase` for variables/functions, `PascalCase` for
  components/types, `kebab-case` for file names.
