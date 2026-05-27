def before_implementing_prompt() -> str:
    """Before I implement something — check org memory for conflicts and constraints."""
    return """\
Before implementing: invoke the `canon` tool with `request` describing what you
intend to build and why, and `context` summarizing what you have already observed
about the codebase — technology choices, existing patterns, relevant libraries.
Canon will return organizational constraints — deprecated patterns, active
migrations, prior failures — that should reshape your plan.

Use this prompt whenever you are about to write or modify code and want to ensure
your approach aligns with current team conventions."""
