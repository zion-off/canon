# 02 — Auth & Onboarding

## Authentication

Email/password authentication. The backend handles all auth logic (password
hashing, JWT issuance, user storage). The frontend is a consumer — it sends
credentials, receives a JWT, stores it in an httpOnly cookie, and attaches it to
all subsequent API requests.

### Login Flow

1. User submits email + password on `/login`.
2. Login form calls the `login` server action (`lib/actions/auth.ts`).
3. Server action calls `POST /api/v1/auth/login` with `{ email, password }`.
4. Backend validates credentials, returns `{ token, user }`.
5. Server action stores `token` in an httpOnly cookie (via `cookies().set()`).
6. Client redirects to `/dashboard`.

### Registration Flow

1. User submits email, name, password on `/register`.
2. Register form calls the `register` server action (`lib/actions/auth.ts`).
3. Server action calls `POST /api/v1/auth/register` with
   `{ email, name, password }`.
4. Backend creates user, returns `{ token, user }` (auto-login on register).
5. Server action stores token in httpOnly cookie, redirects to `/onboarding`
   (user has no tenant yet).

### Session Management

The JWT is stored in an httpOnly cookie — not accessible to client-side
JavaScript. The frontend reads non-sensitive user info (name, email, tenantId)
from a client-accessible cookie or from `GET /api/v1/auth/me` on page load.

### JWT Contents

The backend JWT contains:

```json
{
  "sub": "userId",
  "email": "user@example.com",
  "name": "Alice",
  "tenantId": "tenant_object_id_or_null",
  "role": "owner|member|null",
  "iat": 1234567890,
  "exp": 1234567890
}
```

`tenantId` is `null` until the user completes onboarding.

---

## Backend: `users` Collection

Owned and managed by the backend. The frontend never touches it directly.

```json
{
  "_id": "ObjectId",
  "email": "string",
  "name": "string",
  "passwordHash": "string",
  "tenantId": "ObjectId | null",
  "role": "string",
  "createdAt": "ISODate",
  "updatedAt": "ISODate"
}
```

| Field          | Description                                                               |
| -------------- | ------------------------------------------------------------------------- |
| `email`        | Unique login identifier. Lowercase, trimmed.                              |
| `name`         | Display name.                                                             |
| `passwordHash` | bcrypt hash. Never stored or transmitted in plaintext.                    |
| `tenantId`     | Associated team. `null` until the user completes onboarding.              |
| `role`         | `"owner"` or `"member"`. Owners can generate invite codes and API tokens. |

### Indexes

```javascript
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ tenantId: 1 });
```

---

## Onboarding

Users without a `tenantId` are redirected to `/onboarding` by Next.js
middleware. The onboarding page presents two options:

### Option 1: Create a Team

1. User enters team name.
2. Form calls the `createTeam` server action (`lib/actions/teams.ts`).
3. Server action calls `POST /api/v1/teams/create` with `{ name }`.
4. Backend:
   - Creates a `tenants` document
   - Updates user: `tenantId → tenant._id`, `role → "owner"`
   - Generates a default harness API token
   - Returns `{ tenant, apiToken }` (raw token shown once)
5. Frontend shows success screen with:
   - The raw API token (copy-to-clipboard)
   - MCP config snippets for Cursor / Claude Code / Gemini CLI
   - "Go to Dashboard" button
6. Redirects to `/dashboard`.

### Option 2: Join a Team

1. User enters an invite code.
2. Form calls the `joinTeam` server action (`lib/actions/teams.ts`).
3. Server action calls `POST /api/v1/teams/join` with `{ code }`.
4. Backend:
   - Validates invite code (exists, not expired, uses remaining > 0)
   - Updates user: `tenantId → invite.tenantId`, `role → "member"`
   - Decrements `invite.usesRemaining`
   - Returns `{ tenant }`
5. Redirects to `/dashboard`.

### Backend: `invites` Collection

```json
{
  "_id": "ObjectId",
  "tenantId": "ObjectId",
  "code": "string",
  "createdBy": "ObjectId",
  "usesRemaining": "integer",
  "expiresAt": "ISODate",
  "createdAt": "ISODate"
}
```

| Field           | Description                                                  |
| --------------- | ------------------------------------------------------------ |
| `code`          | 8-character alphanumeric code. Case-insensitive lookup.      |
| `usesRemaining` | Starts at 10 (default). Decremented on each join. 0 = spent. |
| `expiresAt`     | 7 days from creation. Expired codes are rejected.            |
| `createdBy`     | User who generated the code. Must be an owner.               |

### Indexes

```javascript
db.invites.createIndex({ code: 1 }, { unique: true });
db.invites.createIndex({ tenantId: 1 });
db.invites.createIndex({ expiresAt: 1 }, { expireAfterSeconds: 0 }); // TTL cleanup
```

---

## Harness API Token Generation

Team owners can generate harness API tokens from the frontend. The token is
created by the backend and returned to the frontend for one-time display.

1. Owner clicks "Generate Token" on dashboard settings.
2. Form calls the `createToken` server action (`lib/actions/teams.ts`).
3. Server action calls `POST /api/v1/teams/tokens` with `{ label }`.
4. Backend generates token, stores hash, returns raw token.
5. Server action returns raw token to the client component.
6. Client component displays raw token with copy button and MCP config snippet.
7. Token is never shown again after the user navigates away.

---

## Middleware

```typescript
// middleware.ts
import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("canon_token")?.value;
  const { pathname } = request.nextUrl;

  const publicPaths = ["/login", "/register", "/"];
  if (publicPaths.includes(pathname)) return NextResponse.next();

  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Decode JWT to check tenantId (non-sensitive claims only)
  const payload = JSON.parse(atob(token.split(".")[1]));

  if (!payload.tenantId && pathname !== "/onboarding") {
    return NextResponse.redirect(new URL("/onboarding", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
```
