"""Application-owned tools and function-call validation."""

from __future__ import annotations

import json
from typing import Any

COMPONENT_OWNERS: dict[str, str] = {
    "payment": "checkout-platform",
    "identity": "identity-platform",
    "search": "search-platform",
    "unknown": "triage-needed",
}

FUNCTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_component_owner",
            "description": "Trả team phụ trách một software component.",
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "enum": list(COMPONENT_OWNERS),
                    }
                },
                "required": ["component"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
]


def parse_tool_arguments(raw_arguments: str) -> dict[str, Any]:
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Tool arguments không phải JSON hợp lệ: {exc}") from exc

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments phải là JSON object")
    if set(arguments) != {"component"}:
        raise ValueError("Tool arguments phải chỉ chứa field 'component'")

    component = arguments["component"]
    if not isinstance(component, str):
        raise ValueError("component phải là string")
    if component not in COMPONENT_OWNERS:
        raise ValueError(f"Component không hợp lệ: {component}")

    return arguments


def get_component_owner(component: str) -> str:
    return COMPONENT_OWNERS[component]


def execute_tool_call(name: str, raw_arguments: str) -> tuple[dict[str, Any], dict[str, str]]:
    if name != "get_component_owner":
        raise ValueError(f"Tool không được phép: {name}")

    arguments = parse_tool_arguments(raw_arguments)
    component = arguments["component"]
    result = {"component": component, "owner": get_component_owner(component)}
    return arguments, result
