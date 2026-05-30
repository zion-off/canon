"""MCP server instructions — loaded at startup, sent to LLM clients."""

INSTRUCTIONS = """\
Canon is your engineering team's organizational memory — the decisions and the \
reasoning behind them, the conventions, the work in flight, the constraints, \
and the lessons that explain why the codebase is the way it is. The repository \
tells you what the code does today; Canon tells you what the organization has \
already learned.

## When to call the `canon` tool

Call `canon` on your own initiative — before, not after — whenever you are about \
to commit the engineer to a technical direction:

- before recommending or writing an implementation for any non-trivial change
- before choosing a library, pattern, protocol, or architecture
- before modifying infrastructure, auth, data models, or anything other teams
  depend on

Do not wait to be asked. A recommendation can be technically correct yet \
organizationally wrong — cutting against how the team has agreed to work, or \
stepping on something another team is in the middle of. Canon is how you find \
out before the engineer does.

You do not need to call `canon` for trivial edits, formatting, or pure \
questions about the local code. Keep the calls sparse and high-signal.

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
