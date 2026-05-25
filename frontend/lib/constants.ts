export const COOKIE_NAME = "canon_token" as const;

export const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: true,
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 24 * 7,
};

export const API_V1_AUTH = "api/v1/auth" as const;
export const API_V1_SESSIONS = "api/v1/sessions" as const;
export const API_V1_GRAPH = "api/v1/graph" as const;
export const API_V1_TEAMS = "api/v1/teams" as const;

export const ROUTE_ROOT = "/" as const;
export const ROUTE_LOGIN = "/login" as const;
export const ROUTE_REGISTER = "/register" as const;
export const ROUTE_DASHBOARD = "/dashboard" as const;
export const ROUTE_ONBOARDING = "/onboarding" as const;
export const ROUTE_GRAPH = "/graph" as const;
export const ROUTE_SETTINGS = "/settings" as const;

export const PUBLIC_PATHS: readonly string[] = [ROUTE_ROOT, ROUTE_LOGIN, ROUTE_REGISTER];

export function routeToSession(sessionId: string): string {
  return `/sessions/${sessionId}`;
}

export const STATUS = {
  ACTIVE: "active",
  IN_PROGRESS: "in_progress",
  DEPRECATED: "deprecated",
  RESOLVED: "resolved",
  COMPLETED: "completed",
} as const;

export const ROLE_OWNER = "owner" as const;

export const EVENT_TYPE = {
  RUN_STARTED: "run_started",
  RUN_COMPLETED: "run_completed",
  SUBAGENT_INVOKED: "subagent_invoked",
  TOOL_CALL_STARTED: "tool_call_started",
  TOOL_CALL_COMPLETED: "tool_call_completed",
  REASONING_CHECKPOINT: "reasoning_checkpoint",
  FINAL_RESPONSE: "final_response",
} as const;
