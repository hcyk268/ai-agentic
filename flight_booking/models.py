"""
Data models and schemas for the Flight Booking AI Agent system.
Adheres to strict schema validation (Sensor computational & Data Constraints).
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class FlightCriteria(BaseModel):
    """
    Ràng buộc là dữ liệu (Data Constraint):
    Yêu cầu đầu vào và các tiêu chí cố định không bị trôi (Goal Drift) trong quá trình suy luận.
    """
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
    """Mô hình dữ liệu chuyến bay."""
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
    """Mô hình dữ liệu hồ sơ đặt vé trong cơ sở dữ liệu backend."""
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
    """Yêu cầu phê duyệt quyền (Human-in-the-loop permission gate)."""
    action: str
    params: Dict[str, Any]
    reason: str
    current_context: Dict[str, Any]
    suggested_action: str


class HandoffTicket(BaseModel):
    """
    Lớp Harness: Bàn giao cho con người (Slide 48).
    'Bàn giao tốt là bàn giao mà người nhận trả lời được trong 30 giây.'
    """
    ticket_id: str
    status: Literal["stalled", "budget_exhausted", "loop_detected", "needs_approval", "error"]
    summary: str = Field(..., description="Tóm tắt ngắn gọn tình trạng")
    progress_state: str = Field(..., description="Đã làm tới đâu")
    side_effects: List[str] = Field(default_factory=list, description="Hành động nào đã có tác dụng phụ (VD: giữ chỗ, trừ tiền)")
    failed_attempts: List[str] = Field(default_factory=list, description="Hướng nào đã hỏng và vì sao")
    question_for_human: str = Field(..., description="Câu hỏi cụ thể để người nhận ra quyết định ngay")


class ToolResult(BaseModel):
    """
    Chuẩn hóa Structured Output của Tool (Slide 13, 65).
    Đảm bảo agent nhận thông điệp rõ ràng, có gợi ý (hint) khi gặp lỗi.
    """
    status: Literal["success", "not_found", "sold_out", "error", "pending_approval"]
    message: str
    data: Optional[Any] = None
    hint: Optional[str] = None


class AgentRunResult(BaseModel):
    """Kết quả chạy của Agent dùng để đánh giá Benchmark."""
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
