from typing import Dict, Any, Tuple, Optional
from flight_booking.models import ApprovalRequest, FlightCriteria
from flight_booking.mock_tools import get_db


class PermissionManager:
    def __init__(
        self,
        criteria: FlightCriteria,
        require_approval_for_pay: bool = True,
        require_approval_for_non_refundable: bool = True,
        approval_price_threshold: float = 1500000.0,
        auto_approve: bool = False
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

        db = get_db()

        if tool_name == "book_seat":
            flight_id = args.get("flight_id", "").strip().upper()
            flight = db.flights.get(flight_id)

            if flight:
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
                    if flight.price > self.criteria.max_price:
                        pass

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
