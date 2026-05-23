# 03 — Dashboard & Session Pages

## Dashboard (`/dashboard`)

The primary landing page after login. Shows the team's Canon sessions ordered by
most recent activity.

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  Canon                           [Graph] [Settings] [◉]  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Your Sessions                                           │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Payment service retry logic               2m ago   │  │
│  │ 3 runs · summary preview text...                   │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ Auth service JWT rotation                 1h ago   │  │
│  │ 5 runs · summary preview text...                   │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ Billing API migration plan               3h ago    │  │
│  │ 2 runs · summary preview text...                   │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Showing 12 sessions                     [Load more]     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Data Source

```typescript
// Server action (lib/actions/sessions.ts)
import { listSessions } from "@/lib/actions/sessions";

const sessions = await listSessions();
```

### Session Card

Each session card shows:

| Field       | Display                                                |
| ----------- | ------------------------------------------------------ |
| `title`     | Primary text. Auto-generated from first request.       |
| `summary`   | Secondary text. Truncated to ~100 chars. Null = empty. |
| `runCount`  | Badge: "N runs"                                        |
| `lastRunAt` | Relative time: "2m ago", "1h ago", "3 days ago"        |
| `status`    | Dot indicator: green (active), gray (completed)        |

Clicking a card navigates to `/sessions/[sessionId]`.

### Pagination

Cursor-based pagination using `lastRunAt`. "Load more" button fetches the next
20 sessions with `lastRunAt: { $lt: lastVisibleDate }`.

---

## Session Page (`/sessions/[sessionId]`)

Displays the Reasoning Feed — Canon's cognitive trace for a session. This is the
full reasoning timeline: what Canon searched for, what it found, what it
decided, and what it wrote.

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  ← Dashboard    Payment service retry logic              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Session Summary                                         │
│  Explored retry patterns for payment service. Found      │
│  existing exponential backoff convention. Wrote...        │
│                                                          │
│  ─── Run 1 · 2:34 PM ──────────────────────────────────  │
│                                                          │
│  ▶ semantic_retriever started                            │
│                                                          │
│  🔍 tool_call_started                                    │
│     aggregate: payment service retry patterns            │
│                                                          │
│  ✓ tool_call_completed                                   │
│     aggregate completed                                  │
│                                                          │
│  ◆ Reasoning Checkpoint                                  │
│  Found active convention: exponential backoff for all    │
│  inter-service retries. Also found INC-2025-017 where   │
│  missing backoff caused cascade failure.                 │
│                                                          │
│  ▶ graph_explorer started                                │
│                                                          │
│  🔍 tool_call_started                                    │
│     graphLookup: payment-service relationships           │
│                                                          │
│  ✓ tool_call_completed                                   │
│     graphLookup completed                                │
│                                                          │
│  ◆ Reasoning Checkpoint                                  │
│  Payment service connects to 3 downstream services.      │
│  The retry storm incident affected inventory-service.    │
│                                                          │
│  ━━━ Final Response ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Based on organizational memory, here's what you should  │
│  know about retry logic for the payment service...       │
│                                                          │
│  ─── Run 2 · 2:41 PM ──────────────────────────────────  │
│  ...                                                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Data Loading

Two-phase load via server actions. Called from server components or invoked from
the session page's server component tree.

```typescript
// Server action calls (lib/actions/sessions.ts)
import { getSession, getSessionEvents } from "@/lib/actions/sessions";

const session = await getSession(sessionId);
const events = await getSessionEvents(sessionId);
```

### Event Rendering

Events are grouped by `runId` and rendered chronologically within each run.

| Event Type             | Visual Treatment                                       |
| ---------------------- | ------------------------------------------------------ |
| `run_started`          | Run separator with timestamp                           |
| `subagent_invoked`     | Indented label with agent name icon                    |
| `tool_call_started`    | Collapsible card — tool name + summarized args         |
| `tool_call_completed`  | Collapse into the started card as completion indicator |
| `reasoning_checkpoint` | Highlighted card — distinct background, prominent text |
| `final_response`       | Emphasized block — larger text, distinct styling       |
| `run_completed`        | Run separator close                                    |

The `final_response` event (where `isFinal: true`) contains Canon's synthesized
answer — rendered with emphasis at the end of each run.

### Live Streaming

If a session has an active run (recent `run_started` without `run_completed`),
the page connects to a **Next.js Route Handler** that proxies the backend's SSE
stream. This keeps `API_URL` and the harness API token server-side.

The route handler uses the **Edge Runtime** to avoid Vercel's serverless
function timeout limits. Edge Runtime supports long-lived streaming responses —
once the stream starts, it stays alive until the client disconnects or the
backend closes the stream.

#### Route Handler (`app/api/stream/[sessionId]/route.ts`)

```typescript
import { NextRequest } from "next/server";

// Edge Runtime: no serverless timeout on active streams
export const runtime = "edge";

const API_URL = process.env.API_URL!;

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await params;
  const token = request.cookies.get("canon_token")?.value;
  if (!token) return new Response("Unauthorized", { status: 401 });

  // Proxy the SSE stream from the backend (with resume support)
  // JWT auth — backend derives tenant from JWT claim
  const after = request.nextUrl.searchParams.get("after") || "0";
  const upstream = await fetch(
    `${API_URL}/api/v1/sessions/${sessionId}/stream?after=${after}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "text/event-stream",
      },
    },
  );

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
```

**Why Edge Runtime?** Vercel serverless functions have hard max durations (10s
Hobby, 60s Pro). Edge Runtime has a 300s limit — more than sufficient for Canon
runs (seconds to a minute each). The client includes reconnection logic as a
safety net.

#### Client Component

```typescript
// Client-side: connects to the Next.js proxy, not the backend directly
function useEventStream(
  sessionId: string,
  onEvent: (event: AgentEvent) => void,
) {
  useEffect(() => {
    let es: EventSource | null = null;
    let lastSequence = 0;

    function connect() {
      es = new EventSource(`/api/stream/${sessionId}?after=${lastSequence}`);

      es.onmessage = (event) => {
        const data = JSON.parse(event.data);
        lastSequence = data.sequence;
        onEvent(data);
      };

      es.onerror = () => {
        es?.close();
        // Reconnect after brief delay — resumes from lastSequence
        setTimeout(connect, 2000);
      };
    }

    connect();
    return () => es?.close();
  }, [sessionId]);
}
```

The browser never sees `API_URL`. The Next.js route handler forwards the JWT
cookie as a Bearer token to the backend's JWT-authenticated SSE endpoint.

### Run Grouping

Events are grouped into runs by `runId`. Each run displays:

- Run number (sequential, derived from position)
- Timestamp (from the first event's `timestamp`)
- All events in sequence order
- Final response highlighted at the end

If a session has multiple runs, they appear as a vertical timeline — most recent
run at the bottom (chronological order, like a conversation).

---

## Navigation

| Element      | Target           | Behavior                 |
| ------------ | ---------------- | ------------------------ |
| Canon logo   | `/dashboard`     | Always visible in header |
| Graph link   | `/graph`         | Header nav               |
| Back arrow   | `/dashboard`     | Session page header      |
| Session card | `/sessions/[id]` | Dashboard click          |
