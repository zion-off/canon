"""MCP server instructions — loaded at startup, sent to LLM clients."""

INSTRUCTIONS = """\
Canon is your engineering team's organizational memory — the decisions and the \
reasoning behind them, the conventions, the work in flight, the constraints, \
and the lessons that explain why the codebase is the way it is. The repository \
tells you what the code does today; Canon tells you what the organization has \
already learned.

## When to call the `canon` tool

Call `canon` for any code change. Only skip when fixing a typo or adjusting \
whitespace — nothing else.

Your team has accumulated knowledge about how they build software, and you do \
not have this knowledge unless you call Canon. Retry strategies, error handling, \
naming, testing, logging, configuration, validation, caching, concurrency, \
library choices, API design — your team likely has decisions, conventions, or \
lessons about all of these. If you skip Canon, you are guessing at conventions \
your team has already established.

Do not wait to be asked. A recommendation can be technically correct yet \
organizationally wrong — cutting against how the team has agreed to work, \
repeating a mistake the team has already learned from, or stepping on something \
another team is in the middle of. Canon is how you find out before the engineer \
does.

## When not to call

Only for:

- Pure typo or whitespace fixes
- Questions about what the code currently does (reading comprehension)

When in doubt, call it.

## How to call it

- `request`: what you intend to do and why, in natural language. Make it
  specific and domain-rich — "add Redis caching to the user-session service to
  cut database load" beats "add caching." Name the technologies, patterns, and
  services involved ("JWT auth", "gRPC", "billing-api"); Canon cannot see your
  repo, so spell out the identifiers and acronyms that matter.
- `context`: what you have already observed in the codebase — the stack,
  existing patterns, library versions, conventions you can see. This helps Canon
  interpret what it retrieves; it is not used as the search query.

Multiple calls in the same session are tracked automatically — you never manage \
a session ID.

## How to act on the result

Treat Canon's response as authoritative organizational context, not optional \
trivia. Where it contradicts what you were about to do, follow the org and \
adjust your plan. Where it adds something you didn't know — the established way \
to do this, an owner to coordinate with, a constraint to respect, a past \
attempt to learn from — fold it in.

When Canon changes your plan, make the change visible to the engineer: say what \
you were about to do, what Canon surfaced, and how you are adjusting. That \
transparency is the point — the engineer should see the org's memory at work.
"""
