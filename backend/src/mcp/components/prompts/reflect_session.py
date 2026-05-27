from fastmcp.prompts import prompt


@prompt("reflect-session")
def reflect_session_prompt() -> str:
    """Reflect on the current session — capture what was learned, changed, or decided."""
    return """\
Invoke the `canon` tool with a `request` summarizing what was accomplished in this
session: decisions made, patterns discovered, constraints encountered, failures and
their resolutions, and anything the team should know going forward. Include what
was attempted, what was rejected and why, and what was left unresolved.

Use this prompt at the end of a work session to ensure organizational knowledge is
current and nothing important is lost."""
