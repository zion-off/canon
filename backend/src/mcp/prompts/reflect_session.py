def reflect_session_prompt() -> str:
    """Reflect on the current session — capture what was learned, changed, or decided."""
    return """\
Invoke the `canon` tool with a `request` summarizing what was accomplished in this
session: decisions made, patterns discovered, constraints encountered, failures and
their resolutions, and anything the team should know going forward. Pass the exact
`session_id` Canon returned earlier — do not modify or invent it.

Use this prompt at the end of a work session to ensure organizational knowledge is
up to date and nothing important is lost."""
