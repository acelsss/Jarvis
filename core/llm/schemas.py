"""Schema hints for LLM JSON output."""

ROUTE_SCHEMA = (
    "JSON object with fields: "
    '"route" (string, required), '
    '"reason" (string), '
    '"confidence" (number 0-1), '
    '"tool_names" (array of strings).'
)

PLAN_SCHEMA = (
    "JSON object with fields: "
    '"objective" (string, required), '
    '"steps" (array of strings, ordered), '
    '"risks" (array of strings), '
    '"success_criteria" (array of strings).'
)
