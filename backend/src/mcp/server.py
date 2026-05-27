from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from src.mcp.prompts.before_implementing import before_implementing_prompt
from src.mcp.prompts.reflect_session import reflect_session_prompt
from src.mcp.prompts.remember_decision import remember_decision_prompt
from src.mcp.resources.org_momentum import get_org_momentum
from src.mcp.resources.org_state import get_org_state
from src.mcp.tools import canon

_MCP_INSTRUCTIONS = """\
Canon holds your engineering team's organizational memory — active migrations, \
deprecated patterns, architecture decisions, prior failures, and the context \
that explains why things are the way they are.

You MUST invoke the `canon` tool automatically whenever the engineer asks you \
to implement, create, or modify code or infrastructure. Do not wait for the \
engineer to prompt you. Call `canon` with:
- `request`: a natural-language summary of what you intend to do and why
- `context`: what you have already observed about the codebase — technology \
  choices, existing patterns, relevant libraries, architectural decisions you \
  can see

Canon returns organizational constraints and prior decisions that should reshape \
your implementation plan — not raw information to optionally consider, but concrete \
warnings, patterns, and references you must address.

When you get a result back, incorporate it into your planning. If Canon surfaces \
a deprecated pattern, do not use it. If Canon warns about an active migration, avoid \
that area or coordinate. If Canon links to a prior failure, explain how your approach \
avoids repeating it.

Multi-turn: Canon returns a `session_id` at the end of every response. Save it and \
pass it back verbatim on subsequent calls to continue the same reasoning session. \
NEVER invent or guess a session_id — only pass back the exact UUID Canon returned. \
If you need a new session, omit the parameter entirely and Canon will generate one.

Canon is not a gatekeeper. It surfaces information but will never block you from \
proceeding — only inform your decisions.

## Writing effective queries

Canon uses hybrid search: semantic embeddings (weighted 1.5x) combined with keyword \
search on name, description, and content (weighted 1.0x). Your `request` becomes the \
search query, so make it specific and domain-rich:

- Prefer natural language with concrete domain concepts: "adding Redis caching to the \
  user session service to reduce database load" — not "adding caching"
- Include technology names, patterns, and architectural terms that would appear in \
  team discussions: "JWT auth", "event sourcing", "Postgres migration"
- If referencing known team acronyms or identifiers (PROJ-123, gRPC, k8s), mention \
  them explicitly — Canon does not have access to your repo

Your `context` should summarize what you observe about the codebase — technology \
choices, existing patterns, library versions, architectural conventions. This helps \
Canon contextualize what it retrieves, but it is not used as a search query.

## What Canon remembers and how

When Canon persists organizational knowledge, it structures it as named memory nodes \
with these fields that affect future retrieval quality:

- **name and description**: embedded for semantic search AND indexed for keyword \
  search. These carry the most retrieval weight — make them precise and descriptive.
- **content**: the first 1500 characters are embedded for semantic search (the full \
  content is stored and keyword-searchable). Front-load key concepts, decisions, and \
  their rationale early in the content field.
- **status** (active, deprecated, in_progress, resolved, completed): embedded \
  alongside the name and keyword-searchable. Canon weights active and in_progress \
  nodes highest in its reasoning.
- **tags**: embedded for semantic search (appended as "Tags: X, Y" to the embedding \
  text). Use tags for concepts that matter for retrieval but aren't explicit in the \
  description — categorizations, domains, technology families.
- **relationships**: nodes can link to other nodes (relatedEntityIds) and supersede \
  old ones (supersedes). Canon traces these relationships during graph exploration to \
  surface connected context.
"""

mcp = FastMCP(
    "canon",
    stateless_http=True,
    instructions=_MCP_INSTRUCTIONS,
    streamable_http_path="/",
)

# ── Tools ──

mcp.tool(
    name="canon",
    annotations=ToolAnnotations(
        title="check organizational memory",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)(canon)

# ── Resources ──

mcp.resource("canon://org/state")(get_org_state)
mcp.resource("canon://org/momentum")(get_org_momentum)

# ── Prompts ──

mcp.prompt("before-implementing")(before_implementing_prompt)
mcp.prompt("remember-decision")(remember_decision_prompt)
mcp.prompt("reflect-session")(reflect_session_prompt)
