import time
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from flight_booking.models import FlightCriteria, AgentRunResult
from flight_booking.harness.harness_runner import AgentHarness
from flight_booking.mock_tools import FLIGHT_TOOLS
from flight_booking.llm import get_llm


class SubGoal(BaseModel):
    id: int
    title: str
    status: str = "pending"  # pending, in_progress, completed, failed
    notes: Optional[str] = None


class HybridAgent:
    """Agent đặt vé máy bay theo Mẫu Lai."""

    def __init__(self, harness: AgentHarness):
        self.harness = harness
        self.llm = get_llm(temperature=0.0).bind_tools(FLIGHT_TOOLS)
        self.planner_llm = get_llm(temperature=0.0)

    def _create_initial_plan(self) -> List[SubGoal]:
        return [
            SubGoal(id=1, title=f"Tìm kiếm chuyến bay từ {self.harness.criteria.origin} đến {self.harness.criteria.destination} ngày {self.harness.criteria.depart_date}"),
            SubGoal(id=2, title="Kiểm tra chi tiết ghế và giá của chuyến bay tối ưu thỏa mãn ngân sách"),
            SubGoal(id=3, title=f"Đặt giữ chỗ cho hành khách {self.harness.criteria.passenger_name}"),
            SubGoal(id=4, title="Thanh toán vé và nhận xác nhận mã đặt chỗ"),
        ]

    def _replan_if_needed(self, goals: List[SubGoal], last_tool: str, observation: Dict[str, Any]) -> Tuple[List[SubGoal], bool]:
        status = observation.get("status") if isinstance(observation, dict) else ""
        if status in ("sold_out", "not_found", "error"):
            for g in goals:
                if g.status == "in_progress":
                    g.status = "failed"
                    g.notes = f"Thất bại tại {last_tool}: {observation.get('message')}"

            new_goal = SubGoal(
                id=len(goals) + 1,
                title="Tìm kiếm phương án bay dự phòng khác hoặc chuyến bay hãng khác cùng ngày",
                status="pending",
                notes="Phản ứng điều chỉnh kế hoạch sau quan sát ngoại lệ."
            )
            goals.append(new_goal)
            return goals, True

        return goals, False

    def run(self, user_query: str) -> AgentRunResult:
        self.harness.start_session()
        start_time = time.time()

        goals = self._create_initial_plan()
        current_goal_idx = 0

        system_prompt = (
            f"{self.harness.build_system_context()}\n"
            "KIẾN TRÚC MẪU LAI (HYBRID AGENT):\n"
            "Bạn đang vận hành theo danh sách mục tiêu chiến lược (Plan Roadmap).\n"
            "Trong mỗi bước, bạn sẽ suy luận theo phương pháp ReAct để hoàn thành mục tiêu hiện tại.\n"
            "Nếu gặp trở ngại (hết vé, lỗi), hệ thống sẽ kích hoạt tái lập kế hoạch (Dynamic Replanning).\n"
        )

        messages: List[Any] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query)
        ]

        termination_reason = "MAX_STEPS_REACHED"
        handoff_ticket = None

        while self.harness.step_count < self.harness.max_steps:
            active_goal = None
            for g in goals:
                if g.status == "pending":
                    g.status = "in_progress"
                    active_goal = g
                    break
                elif g.status == "in_progress":
                    active_goal = g
                    break

            plan_summary = "\n".join([f"[{g.status.upper()}] Bước {g.id}: {g.title}" for g in goals])
            context_msg = f"TIẾN ĐỘ KẾ HOẠCH HIỆN TẠI:\n{plan_summary}\nMục tiêu hiện tại: {active_goal.title if active_goal else 'Hoàn tất'}"

            self.harness.llm_call_count += 1
            prompt_with_plan = messages + [HumanMessage(content=f"[System Status Update]: {context_msg}")]

            try:
                ai_msg = self.llm.invoke(prompt_with_plan)
            except Exception as e:
                termination_reason = "LLM_ERROR"
                break

            messages.append(ai_msg)

            if not ai_msg.tool_calls:
                verified, _ = self.harness.final_verification()
                if verified:
                    termination_reason = "GOAL_ACHIEVED"
                else:
                    termination_reason = "STOPPED_WITHOUT_GOAL"
                break

            should_terminate = False
            for tool_call in ai_msg.tool_calls:
                t_name = tool_call["name"]
                t_args = tool_call["args"]
                t_id = tool_call.get("id", f"call_hybrid_{self.harness.step_count}")

                obs, term_code, handoff = self.harness.execute_tool_with_harness(t_name, t_args)

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

                goals, replanned = self._replan_if_needed(goals, t_name, obs)
                if not replanned and obs.get("status") == "success":
                    if active_goal:
                        active_goal.status = "completed"

            if should_terminate:
                break

        duration = time.time() - start_time
        verified, verif_msg = self.harness.final_verification()

        return AgentRunResult(
            agent_name="HybridAgent",
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
