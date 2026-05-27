from fastmcp.prompts import prompt


@prompt("before-implementing")
def before_implementing_prompt() -> str:
    """Before I implement something — check org memory for conflicts and constraints."""
    return """\
Invoke the `canon` tool whenever you are about to recommend an implementation
approach, make an architectural choice, select a technology or library, or give
any advice that commits the engineer to a direction. Canon holds organizational
memory that the codebase cannot tell you — and your recommendation may be
technically correct but organizationally wrong without this context.

When invoking: set `request` to describe the engineering intent (what you intend
to recommend and why). Set `context` to summarize what you have already observed
— the current technology stack, existing patterns, scope of the change, and any
relevant codebase details.

If Canon returns a reshaped plan, use that plan instead of your original
recommendation."""
