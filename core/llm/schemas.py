"""Schema hints for LLM JSON output."""

ROUTE_SCHEMA = (
    "JSON object with fields: "
    '"route" (string, required), '
    '"reason" (string), '
    '"confidence" (number 0-1), '
    '"tool_names" (array of strings).'
)

ROUTE_SCHEMA_V0_2 = (
    "RouteDecision JSON object with fields: "
    '"route_type" (string enum: qa|skill|tool|mcp|clarify, required), '
    '"reason" (string, required), '
    '"confidence" (number 0-1), '
    '"skill_id" (string, required if route_type=skill), '
    '"tool_ids" (array of strings, required if route_type=tool or mcp), '
    '"clarify_questions" (array of strings, required if route_type=clarify).'
)

CAPABILITY_INDEX_SCHEMA_HINT = (
    "Capability index items include: "
    '"id" (string), '
    '"name" (string), '
    '"type" (string enum: skill|tool|mcp), '
    '"tags" (array of strings), '
    '"description" (string, short summary).'
)

PLAN_SCHEMA = (
    "JSON object with fields: "
    '"objective" (string, required), '
    '"steps" (array of strings, ordered), '
    '"risks" (array of strings), '
    '"success_criteria" (array of strings).'
)
