from typing import Tuple, Optional, Dict, Any
from flight_booking.models import FlightCriteria, BookingRecord
from flight_booking.mock_tools import get_db


class CompletionVerifier:
    def __init__(self, criteria: FlightCriteria):
        self.criteria = criteria

    def verify_booking(self, booking_id: Optional[str]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        if not booking_id:
            return False, "Chưa có booking_id được ghi nhận.", None

        db = get_db()
        booking = db.bookings.get(booking_id)

        if not booking:
            return False, f"Mã đặt chỗ {booking_id} không tồn tại.", None

        # 1. Kiểm tra trạng thái và thanh toán
        if booking.status != "confirmed":
            return False, f"Vé chưa được xác nhận hoàn tất (trạng thái hiện tại: '{booking.status}').", booking.model_dump()

        if not booking.paid:
            return False, "Vé chưa được thanh toán thành công (paid=False).", booking.model_dump()

        # 2. Kiểm tra thông tin hành khách
        if booking.passenger_name.strip().lower() != self.criteria.passenger_name.strip().lower():
            return False, f"Tên hành khách không khớp: yêu cầu '{self.criteria.passenger_name}', trên vé '{booking.passenger_name}'.", booking.model_dump()

        # 3. Kiểm tra chéo thông tin chuyến bay tương ứng
        flight = db.flights.get(booking.flight_id)
        if not flight:
            return False, f"Chuyến bay {booking.flight_id} không tồn tại trong hệ thống.", booking.model_dump()

        if flight.origin.upper() != self.criteria.origin.upper():
            return False, f"Chuyến bay xuất phát từ {flight.origin}, không phải {self.criteria.origin}.", booking.model_dump()

        if flight.destination.upper() != self.criteria.destination.upper():
            return False, f"Chuyến bay đến {flight.destination}, không phải {self.criteria.destination}.", booking.model_dump()

        if flight.depart_date != self.criteria.depart_date:
            return False, f"Ngày bay trên vé {flight.depart_date} không khớp ngày yêu cầu {self.criteria.depart_date}.", booking.model_dump()

        if booking.price > self.criteria.max_price:
            return False, f"Giá vé thanh toán ({booking.price:,.0f}đ) vượt quá ngân sách ({self.criteria.max_price:,.0f}đ).", booking.model_dump()

        if self.criteria.preferred_time == "morning" and flight.depart_time >= "12:00":
            return False, f"Giờ bay {flight.depart_time} không phải buổi sáng (<12:00).", booking.model_dump()

        return True, "Vé đã hoàn tất, hợp lệ 100% với mọi tiêu chí ràng buộc.", booking.model_dump()
