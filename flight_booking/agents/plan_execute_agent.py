import time
import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from flight_booking.models import FlightCriteria, AgentRunResult
from flight_booking.harness.harness_runner import AgentHarness
from flight_booking.llm import get_llm


class PlanStep(BaseModel):
    step_id: int
    tool: str = Field(..., description="Tên tool cần gọi (search_flights, check_seat, book_seat, pay)")
    args_template: Dict[str, Any] = Field(..., description="Tham số, có thể chứa placeholder như $FLIGHT_ID, $SEAT, $BOOKING_ID")
    purpose: str


class ExecutionPlan(BaseModel):
    steps: List[PlanStep]
    estimated_steps: int
    rationale: str


class PlanThenExecuteAgent:
    """Agent đặt vé máy bay theo mẫu thiết kế Plan-then-Execute."""

    def __init__(self, harness: AgentHarness):
        self.harness = harness
        self.llm = get_llm(temperature=0.0)

    def generate_plan(self, user_query: str) -> ExecutionPlan:
        system_prompt = (
            "Bạn là Chuyên gia Lập kế hoạch (Planner) cho hệ thống đặt vé máy bay.\n"
            "Hãy phân tích yêu cầu và trả về một kế hoạch JSON các bước thực thi công cụ.\n"
            "Các công cụ khả dụng:\n"
            "1. search_flights(origin, destination, depart_date)\n"
            "2. check_seat(flight_id)\n"
            "3. book_seat(flight_id, seat_number, passenger_name)\n"
            "4. pay(booking_id, payment_method)\n\n"
            "ĐỊNH DẠNG JSON BẮT BUỘC:\n"
            "{\n"
            '  "steps": [\n'
            '    {"step_id": 1, "tool": "search_flights", "args_template": {"origin": "SGN", "destination": "DAD", "depart_date": "2026-10-07"}, "purpose": "Tìm chuyến bay"},\n'
            '    {"step_id": 2, "tool": "check_seat", "args_template": {"flight_id": "$FLIGHT_ID"}, "purpose": "Kiểm tra ghế trống"},\n'
            '    {"step_id": 3, "tool": "book_seat", "args_template": {"flight_id": "$FLIGHT_ID", "seat_number": "$SEAT", "passenger_name": "Tên"}, "purpose": "Giữ chỗ"},\n'
            '    {"step_id": 4, "tool": "pay", "args_template": {"booking_id": "$BOOKING_ID", "payment_method": "corp_card"}, "purpose": "Thanh toán vé"}\n'
            "  ],\n"
            '  "estimated_steps": 4,\n'
            '  "rationale": "Lý do chọn chuỗi bước này"\n'
            "}\n"
            "Chỉ trả về duy nhất khối JSON, không giải thích thêm."
        )

        user_content = (
            f"Thông tin yêu cầu đặt vé:\n"
            f"- Điểm đi: {self.harness.criteria.origin}\n"
            f"- Điểm đến: {self.harness.criteria.destination}\n"
            f"- Ngày bay: {self.harness.criteria.depart_date}\n"
            f"- Hành khách: {self.harness.criteria.passenger_name}\n"
            f"- Ngân sách tối đa: {self.harness.criteria.max_price:,.0f} VNĐ\n"
            f"- Khung giờ ưu tiên: {self.harness.criteria.preferred_time}\n"
            f"Yêu cầu: {user_query}"
        )

        resp = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content)
        ])
        self.harness.llm_call_count += 1

        text = resp.content.strip()
        json_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
            return ExecutionPlan(**data)

        return ExecutionPlan(
            steps=[
                PlanStep(step_id=1, tool="search_flights", args_template={"origin": self.harness.criteria.origin, "destination": self.harness.criteria.destination, "depart_date": self.harness.criteria.depart_date}, purpose="Tìm chuyến bay"),
                PlanStep(step_id=2, tool="check_seat", args_template={"flight_id": "$FLIGHT_ID"}, purpose="Kiểm tra ghế và giá"),
                PlanStep(step_id=3, tool="book_seat", args_template={"flight_id": "$FLIGHT_ID", "seat_number": "$SEAT", "passenger_name": self.harness.criteria.passenger_name}, purpose="Giữ chỗ"),
                PlanStep(step_id=4, tool="pay", args_template={"booking_id": "$BOOKING_ID", "payment_method": "corp_card"}, purpose="Thanh toán vé"),
            ],
            estimated_steps=4,
            rationale="Quy trình tuần tự mặc định"
        )

    def run(self, user_query: str) -> AgentRunResult:
        self.harness.start_session()
        start_time = time.time()

        try:
            plan = self.generate_plan(user_query)
        except Exception as e:
            return AgentRunResult(
                agent_name="PlanThenExecuteAgent",
                scenario_id=f"{self.harness.criteria.origin}-{self.harness.criteria.destination}",
                success=False,
                termination_reason="PLANNING_FAILED",
                steps_count=0,
                llm_call_count=self.harness.llm_call_count,
                duration_sec=round(time.time() - start_time, 2),
                error_message=f"Lỗi lập kế hoạch: {str(e)}"
            )

        resolved_state: Dict[str, Any] = {
            "origin": self.harness.criteria.origin,
            "destination": self.harness.criteria.destination,
            "depart_date": self.harness.criteria.depart_date,
            "passenger_name": self.harness.criteria.passenger_name,
            "flight_id": None,
            "seat_number": None,
            "booking_id": None
        }

        termination_reason = "PLAN_COMPLETED"
        handoff_ticket = None

        for step in plan.steps:
            if self.harness.step_count >= self.harness.max_steps:
                termination_reason = "BUDGET_EXHAUSTED"
                break

            args = {}
            for k, v in step.args_template.items():
                if v == "$FLIGHT_ID":
                    args[k] = resolved_state.get("flight_id")
                elif v == "$SEAT":
                    args[k] = resolved_state.get("seat_number")
                elif v == "$BOOKING_ID":
                    args[k] = resolved_state.get("booking_id")
                elif v == "$PASSENGER_NAME":
                    args[k] = resolved_state.get("passenger_name")
                else:
                    args[k] = v

            obs, term_code, handoff = self.harness.execute_tool_with_harness(step.tool, args)

            if term_code:
                termination_reason = term_code
                handoff_ticket = handoff
                break

            status = obs.get("status") if isinstance(obs, dict) else None
            data = obs.get("data") if isinstance(obs, dict) else None

            if step.tool == "search_flights":
                if status == "success" and isinstance(data, list) and len(data) > 0:
                    valid_f = None
                    for f in data:
                        if f.get("price", float("inf")) <= self.harness.criteria.max_price:
                            valid_f = f
                            break
                    if valid_f:
                        resolved_state["flight_id"] = valid_f.get("flight_id")
                    else:
                        termination_reason = "STEP_FAILED_NO_SUITABLE_FLIGHT"
                        break
                else:
                    termination_reason = "STEP_FAILED_FLIGHTS_NOT_FOUND"
                    break

            elif step.tool == "check_seat":
                if status == "success" and isinstance(data, dict):
                    avail_seats = data.get("available_seats", [])
                    if avail_seats:
                        resolved_state["seat_number"] = avail_seats[0]
                    else:
                        termination_reason = "STEP_FAILED_SEAT_SOLD_OUT"
                        break
                else:
                    termination_reason = "STEP_FAILED_SEAT_CHECK"
                    break

            elif step.tool == "book_seat":
                if status == "success" and isinstance(data, dict):
                    resolved_state["booking_id"] = data.get("booking_id")
                else:
                    termination_reason = "STEP_FAILED_BOOKING"
                    break

            elif step.tool == "pay":
                if status != "success":
                    termination_reason = "STEP_FAILED_PAYMENT"
                    break

        duration = time.time() - start_time
        verified, verif_msg = self.harness.final_verification()

        return AgentRunResult(
            agent_name="PlanThenExecuteAgent",
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
