"""Main Issue Triage workflow."""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from .models import IssueTriage, ToolTrace, TriageRun, validate_issue_triage
from .prompts import build_messages
from .tools import FUNCTION_TOOLS, execute_tool_call


def _assistant_message_to_dict(message: Any) -> dict[str, Any]:
    tool_calls = []
    for call in (getattr(message, "tool_calls", None) or []):
        tool_calls.append(
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
        )

    return {
        "role": "assistant",
        "content": getattr(message, "content", None),
        "tool_calls": tool_calls,
    }


def _parse_json_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("Model không trả về JSON object hợp lệ.")
        try:
            payload = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("Không parse được JSON IssueTriage.") from exc

    if not isinstance(payload, dict):
        raise ValueError("IssueTriage phải là JSON object.")
    return payload


def _parse_final_response(response: Any) -> IssueTriage:
    message = response.choices[0].message
    parsed = getattr(message, "parsed", None)
    if parsed is not None:
        return validate_issue_triage(parsed)

    content = getattr(message, "content", None) or ""
    return validate_issue_triage(_parse_json_text(content))


def _request_structured_output(
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
) -> IssueTriage:
    try:
        response = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=IssueTriage,
        )
        return _parse_final_response(response)
    except Exception:
        fallback_messages = messages + [
            {
                "role": "user",
                "content": (
                    "Chỉ trả về một JSON object đúng schema IssueTriage. "
                    "Không markdown, không giải thích thêm.\n"
                    f"Schema: {json.dumps(IssueTriage.model_json_schema(), ensure_ascii=False)}"
                ),
            }
        ]
        response = client.chat.completions.create(
            model=model,
            messages=fallback_messages,
        )
        return _parse_final_response(response)


def triage_issue(client: OpenAI, model: str, issue: str) -> TriageRun:
    issue = issue.strip()
    if not issue:
        raise ValueError("Issue không được để trống.")
    if len(issue) > 5000:
        raise ValueError("Issue quá dài; giới hạn 5000 ký tự.")

    messages = build_messages(issue)

    first_response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=FUNCTION_TOOLS,
        tool_choice="required",
    )
    assistant_message = first_response.choices[0].message
    tool_calls = assistant_message.tool_calls or []
    if not tool_calls:
        raise RuntimeError("Model không tạo tool_call dù tool_choice='required'.")

    messages.append(_assistant_message_to_dict(assistant_message))

    traces: list[ToolTrace] = []
    for call in tool_calls:
        arguments, result = execute_tool_call(call.function.name, call.function.arguments)
        traces.append(
            ToolTrace(
                call_id=call.id,
                name=call.function.name,
                arguments=arguments,
                result=result,
            )
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )

    triage = _request_structured_output(client, model, messages)
    return TriageRun(triage=triage, tool_traces=tuple(traces))
