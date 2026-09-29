import uuid
from typing import List, Dict, Any, Optional
from flight_booking.models import HandoffTicket, FlightCriteria


class HandoffManager:
    @staticmethod
    def create_ticket(
        status: str,
        summary: str,
        progress_state: str,
        side_effects: List[str],
        failed_attempts: List[str],
        question_for_human: str
    ) -> HandoffTicket:
        ticket_id = f"TICKET-{uuid.uuid4().hex[:6].upper()}"
        return HandoffTicket(
            ticket_id=ticket_id,
            status=status,
            summary=summary,
            progress_state=progress_state,
            side_effects=side_effects,
            failed_attempts=failed_attempts,
            question_for_human=question_for_human
        )

    @staticmethod
    def create_permission_handoff(
        criteria: FlightCriteria,
        action: str,
        params: Dict[str, Any],
        reason: str,
        context: Dict[str, Any]
    ) -> HandoffTicket:
        side_effects = []
        if context.get("held_booking_id"):
            side_effects.append(f"Đã tạm giữ ghế với mã đặt chỗ: {context.get('held_booking_id')}")

        question = (
            f"Hệ thống chuẩn bị thực hiện '{action}' với tham số {params}. "
            f"Lý do cần xác nhận: {reason}. Bạn có phê duyệt hành động này không? (Đồng ý / Từ chối)"
        )

        return HandoffTicket(
            ticket_id=f"APPR-{uuid.uuid4().hex[:6].upper()}",
            status="needs_approval",
            summary=f"Yêu cầu phê duyệt hành động nhạy cảm: {action}",
            progress_state=f"Đã chọn được chuyến bay và thông tin đặt chỗ phù hợp với hành khách {criteria.passenger_name}.",
            side_effects=side_effects,
            failed_attempts=context.get("failed_attempts", []),
            question_for_human=question
        )

    @staticmethod
    def create_budget_exhausted_handoff(
        context: Dict[str, Any],
        criteria: FlightCriteria,
        max_steps: int
    ) -> HandoffTicket:
        side_effects = []
        if context.get("held_booking_id"):
            side_effects.append(f"Mã đặt chỗ {context.get('held_booking_id')} đang ở trạng thái tạm giữ (chưa thanh toán).")

        return HandoffTicket(
            ticket_id=f"HO-BUDGET-{uuid.uuid4().hex[:6].upper()}",
            status="budget_exhausted",
            summary=f"Agent đã chạm giới hạn ngân sách ({max_steps} bước) mà chưa hoàn tất xuất vé.",
            progress_state=f"Chuyến bay đã xem xét: {context.get('last_flight_id', 'Chưa chọn')}. Tiến độ: {context.get('progress_description', 'Đang tìm kiếm')}.",
            side_effects=side_effects,
            failed_attempts=context.get("failed_attempts", []),
            question_for_human=f"Bạn có muốn tăng thêm số vòng lặp hay muốn nhân viên tiếp quản thủ công?"
        )

    @staticmethod
    def create_loop_or_stall_handoff(
        status_type: str,
        context: Dict[str, Any],
        criteria: FlightCriteria,
        details: str
    ) -> HandoffTicket:
        return HandoffTicket(
            ticket_id=f"HO-LOOP-{uuid.uuid4().hex[:6].upper()}",
            status="loop_detected" if status_type == "LOOP" else "stalled",
            summary=f"Cảnh báo Harness: Phát hiện {status_type} ({details}).",
            progress_state=f"Tiến trình bị ngưng trệ khi xử lý yêu cầu {criteria.origin} -> {criteria.destination} ngày {criteria.depart_date}.",
            side_effects=[f"Đã giữ chỗ {context.get('held_booking_id')}"] if context.get("held_booking_id") else ["Không có tác dụng phụ."],
            failed_attempts=context.get("failed_attempts", []),
            question_for_human="Agent không thể tiến triển thêm do lặp lại thao tác hoặc không tìm thấy giải pháp thỏa mãn. Bạn muốn đổi tiêu chí (ngày/giá) hay hủy tác vụ?"
        )
