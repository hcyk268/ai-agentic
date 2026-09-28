"""
Harness Layer 3: Kiểm quyền (Permission & Authorization Gateway).
Slide 35, 41: Chạy TRƯỚC KHI THỰC THI TOOL.
Ngăn chặn các hành động nhạy cảm hoặc vượt thẩm quyền:
- Thanh toán tài chính (pay)
- Đặt vé không hoàn hủy (non-refundable ticket)
- Đặt vé vượt ngưỡng chi tiêu cho phép mà chưa có người duyệt
"""

from typing import Dict, Any, Tuple, Optional
from flight_booking.models import ApprovalRequest, FlightCriteria
from flight_booking.mock_tools import get_db


class PermissionManager:
    """Quản lý thẩm quyền và cổng phê duyệt cho Agent."""

    def __init__(
        self,
        criteria: FlightCriteria,
        require_approval_for_pay: bool = True,
        require_approval_for_non_refundable: bool = True,
        approval_price_threshold: float = 1500000.0,
        auto_approve: bool = False  # Dùng khi chạy benchmark tự động có giả lập phê duyệt
    ):
        self.criteria = criteria
        self.require_approval_for_pay = require_approval_for_pay
        self.require_approval_for_non_refundable = require_approval_for_non_refundable
        self.approval_price_threshold = approval_price_threshold
        self.auto_approve = auto_approve

    def check_tool_permission(
        self,
        tool_name: str,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[ApprovalRequest]]:
        """
        Kiểm tra quyền thực thi trước khi gọi tool.
        Trả về: (được phép thực thi, yêu cầu phê duyệt nếu bị chặn)
        """
        db = get_db()

        # 1. Kiểm tra quyền khi đặt ghế (book_seat)
        if tool_name == "book_seat":
            flight_id = args.get("flight_id", "").strip().upper()
            flight = db.flights.get(flight_id)

            if flight:
                # Kiểm tra vé không hoàn hủy và vượt ngưỡng giá
                is_non_refundable = not flight.refundable
                exceeds_threshold = flight.price > self.approval_price_threshold

                if is_non_refundable and self.require_approval_for_non_refundable:
                    if not self.auto_approve:
                        req = ApprovalRequest(
                            action="book_seat",
                            params=args,
                            reason=f"Chuyến bay {flight_id} có điều kiện 'Không hoàn vé' (Non-refundable) và giá {flight.price:,.0f}đ.",
                            current_context={
                                "flight_id": flight.flight_id,
                                "airline": flight.airline,
                                "price": flight.price,
                                "refundable": flight.refundable,
                                "seat": args.get("seat_number")
                            },
                            suggested_action="Xác nhận đặt vé không hoàn hủy hay tìm chuyến khác có hỗ trợ hoàn vé."
                        )
                        return False, req

                if exceeds_threshold:
                    # Nếu vượt ngân sách tối đa của người dùng thì từ chối ngay lập tức
                    if flight.price > self.criteria.max_price:
                        # Ràng buộc cứng: không cho phép vượt max_price
                        pass

        # 2. Kiểm tra quyền khi thanh toán (pay)
        if tool_name == "pay":
            booking_id = args.get("booking_id", "").strip()
            booking = db.bookings.get(booking_id)

            if booking and self.require_approval_for_pay:
                if not self.auto_approve:
                    req = ApprovalRequest(
                        action="pay",
                        params=args,
                        reason=f"Thực hiện giao dịch thanh toán tài chính {booking.price:,.0f}đ cho mã đặt chỗ {booking_id}.",
                        current_context={
                            "booking_id": booking.booking_id,
                            "price": booking.price,
                            "passenger": booking.passenger_name,
                            "flight_id": booking.flight_id
                        },
                        suggested_action=f"Xác nhận thanh toán {booking.price:,.0f}đ bằng {args.get('payment_method', 'corp_card')}."
                    )
                    return False, req

        return True, None
