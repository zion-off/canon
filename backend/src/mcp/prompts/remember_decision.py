def remember_decision_prompt() -> str:
    """Remember a decision, constraint, or pattern the team should know about."""
    return """\
Invoke the `canon` tool with a `request` that clearly states the decision, constraint,
or pattern you want to capture — include the reasoning, alternatives considered and
rejected, and any relationships to existing systems or decisions. Provide enough
context (technology stack, affected systems, ownership) so Canon can link this
memory to the right entities.

Use this prompt after making a significant design choice, discovering a non-obvious
constraint, or establishing a pattern others should follow."""
