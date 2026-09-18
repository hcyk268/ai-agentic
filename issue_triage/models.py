"""Domain models and output contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class IssueTriage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["classified", "insufficient_data", "out_of_scope"]
    severity: Literal["P0", "P1", "P2", "P3"] | None = None
    component: str | None = None
    needs_urgent_response: bool = False
    reason: str = Field(min_length=1, max_length=500)


@dataclass(frozen=True)
class ToolTrace:

    call_id: str
    name: str
    arguments: dict[str, Any]
    result: dict[str, str]


@dataclass(frozen=True)
class TriageRun:

    triage: IssueTriage
    tool_traces: tuple[ToolTrace, ...]


def validate_issue_triage(payload: Any) -> IssueTriage:
    try:
        return IssueTriage.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"IssueTriage không hợp lệ: {exc}") from exc
