"""
Data models and schemas.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class FlightCriteria(BaseModel):
    origin: str = Field(..., description="Mã sân bay đi (VD: SGN, HAN, DAD)")
    destination: str = Field(..., description="Mã sân bay đến (VD: SGN, HAN, DAD)")
    depart_date: str = Field(..., description="Ngày bay theo định dạng YYYY-MM-DD")
    passenger_name: str = Field(..., description="Họ và tên hành khách")
    max_price: float = Field(..., description="Ngân sách tối đa cho vé (VNĐ)")
    preferred_time: Optional[Literal["morning", "afternoon", "evening", "any"]] = Field(
        default="any",
        description="Khung giờ ưu tiên: morning (<12:00), afternoon (12:00-18:00), evening (>18:00)"
    )


class Flight(BaseModel):
    flight_id: str
    airline: str
    origin: str
    destination: str
    depart_date: str
    depart_time: str
    price: float
    available_seats: List[str]
    refundable: bool = True
    seat_class: str = "Economy"


class BookingRecord(BaseModel):
    booking_id: str
    flight_id: str
    passenger_name: str
    seat_number: str
    price: float
    status: Literal["held", "confirmed", "cancelled", "expired"] = "held"
    paid: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    refundable: bool = True


class ApprovalRequest(BaseModel):
    action: str
    params: Dict[str, Any]
    reason: str
    current_context: Dict[str, Any]
    suggested_action: str


class HandoffTicket(BaseModel):
    ticket_id: str
    status: Literal["stalled", "budget_exhausted", "loop_detected", "needs_approval", "error"]
    summary: str = Field(..., description="Tóm tắt ngắn gọn tình trạng")
    progress_state: str = Field(..., description="Đã làm tới đâu")
    side_effects: List[str] = Field(default_factory=list, description="Hành động nào đã có tác dụng phụ (VD: giữ chỗ, trừ tiền)")
    failed_attempts: List[str] = Field(default_factory=list, description="Hướng nào đã hỏng và vì sao")
    question_for_human: str = Field(..., description="Câu hỏi cụ thể để người nhận ra quyết định ngay")


class ToolResult(BaseModel):
    status: Literal["success", "not_found", "sold_out", "error", "pending_approval"]
    message: str
    data: Optional[Any] = None
    hint: Optional[str] = None


class AgentRunResult(BaseModel):
    agent_name: str
    scenario_id: str
    success: bool
    termination_reason: str
    booking_id: Optional[str] = None
    steps_count: int = 0
    llm_call_count: int = 0
    duration_sec: float = 0.0
    history: List[Dict[str, Any]] = Field(default_factory=list)
    handoff_ticket: Optional[HandoffTicket] = None
    verification_passed: bool = False
    error_message: Optional[str] = None
