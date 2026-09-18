#!/usr/bin/env python3
"""CLI entry point for Issue Triage."""

from __future__ import annotations

import argparse
import json

from .config import model_name, openai_client
from .models import TriageRun
from .prompts import DEFAULT_ISSUE
from .service import triage_issue


def print_trace(result: TriageRun) -> None:
    for index, trace in enumerate(result.tool_traces, start=1):
        print(f"\n=== {index}. tool_call ===")
        print(
            json.dumps(
                {
                    "id": trace.call_id,
                    "name": trace.name,
                    "arguments": trace.arguments,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        print("\n=== application executes ===")
        print(
            f"get_component_owner({trace.arguments['component']!r})"
            f" -> {trace.result['owner']!r}"
        )

        print("\n=== tool_result ===")
        print(json.dumps(trace.result, ensure_ascii=False, indent=2))

    print("\n=== final response ===")
    print(result.triage.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", default=DEFAULT_ISSUE, help="Nội dung issue cần triage.")
    args = parser.parse_args()

    result = triage_issue(openai_client(), model_name(), args.issue)
    print_trace(result)


if __name__ == "__main__":
    main()
