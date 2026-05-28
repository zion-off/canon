"""MCP server instructions — loaded at startup, sent to LLM clients."""

INSTRUCTIONS = """\
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

Multiple calls to `canon` within the same MCP session are automatically tracked — \
you don't need to manage any session ID. The MCP transport handles session continuity.

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
"""
