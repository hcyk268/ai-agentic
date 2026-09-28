"""
Mẫu thiết kế 1: ReAct Agent (Reasoning + Acting).
Triển khai theo slide 18-21:
Suy luận (Thought) -> Hành động (Action: Tool call) -> Quan sát (Observation) -> Lặp lại.
Tích hợp trực tiếp lớp Harness để kiểm soát mọi hành vi.
"""

import time
import json
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from flight_booking.models import FlightCriteria, AgentRunResult
from flight_booking.harness.harness_runner import AgentHarness
from flight_booking.mock_tools import FLIGHT_TOOLS
from flight_booking.llm import get_llm


class ReActAgent:
    """Agent đặt vé máy bay theo mẫu thiết kế ReAct."""

    def __init__(self, harness: AgentHarness):
        self.harness = harness
        self.llm = get_llm(temperature=0.0).bind_tools(FLIGHT_TOOLS)

    def run(self, user_query: str) -> AgentRunResult:
        """Thực thi chu trình ReAct dưới sự giám sát của AgentHarness."""
        self.harness.start_session()
        start_time = time.time()

        system_prompt = self.harness.build_system_context()
        messages: List[Any] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query)
        ]

        termination_reason = "MAX_STEPS_REACHED"
        handoff_ticket = None

        while self.harness.step_count < self.harness.max_steps:
            # 1. Suy luận (LLM reasoning & tool proposal)
            self.harness.llm_call_count += 1
            try:
                ai_msg = self.llm.invoke(messages)
            except Exception as e:
                termination_reason = "LLM_ERROR"
                break

            messages.append(ai_msg)

            # Nếu model không gọi tool nào nữa
            if not ai_msg.tool_calls:
                # Kiểm tra xem có phải đã đạt mục tiêu không
                verified, _ = self.harness.final_verification()
                if verified:
                    termination_reason = "GOAL_ACHIEVED"
                else:
                    termination_reason = "STOPPED_WITHOUT_GOAL"
                break

            # 2. Hành động & Quan sát qua Harness
            should_terminate = False
            for tool_call in ai_msg.tool_calls:
                t_name = tool_call["name"]
                t_args = tool_call["args"]
                t_id = tool_call.get("id", f"call_{self.harness.step_count}")

                # Chạy qua các chốt chặn của Harness
                obs, term_code, handoff = self.harness.execute_tool_with_harness(t_name, t_args)

                # Nạp observation vào chuỗi hội thoại
                messages.append(ToolMessage(
                    tool_call_id=t_id,
                    name=t_name,
                    content=json.dumps(obs, ensure_ascii=False)
                ))

                if term_code:
                    termination_reason = term_code
                    handoff_ticket = handoff
                    should_terminate = True
                    break

            if should_terminate:
                break

        duration = time.time() - start_time
        verified, verif_msg = self.harness.final_verification()

        return AgentRunResult(
            agent_name="ReActAgent",
            scenario_id=f"{self.harness.criteria.origin}-{self.harness.criteria.destination}",
            success=verified,
            termination_reason=termination_reason,
            booking_id=self.harness.context.get("held_booking_id"),
            steps_count=self.harness.step_count,
            llm_call_count=self.harness.llm_call_count,
            duration_sec=round(duration, 2),
            history=self.harness.history_trace,
            handoff_ticket=handoff_ticket,
            verification_passed=verified,
            error_message=None if verified else verif_msg
        )
