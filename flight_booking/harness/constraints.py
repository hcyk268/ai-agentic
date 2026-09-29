from typing import Dict, Any, Tuple
from flight_booking.models import FlightCriteria, Flight, BookingRecord


class DataConstraintManager:
    def __init__(self, criteria: FlightCriteria):
        self.criteria = criteria

    def validate_flight_against_criteria(self, flight: Flight) -> Tuple[bool, str]:
        """Kiểm tra chuyến bay thỏa mãn các ràng buộc."""
        if flight.origin.upper() != self.criteria.origin.upper():
            return False, f"Sai điểm đi: yêu cầu {self.criteria.origin}, thực tế {flight.origin}"

        if flight.destination.upper() != self.criteria.destination.upper():
            return False, f"Sai điểm đến: yêu cầu {self.criteria.destination}, thực tế {flight.destination}"

        if flight.depart_date != self.criteria.depart_date:
            return False, f"Sai ngày bay: yêu cầu {self.criteria.depart_date}, thực tế {flight.depart_date}"

        if flight.price > self.criteria.max_price:
            return False, f"Vượt ngân sách: giá {flight.price:,.0f}đ > tối đa {self.criteria.max_price:,.0f}đ"

        if self.criteria.preferred_time == "morning" and flight.depart_time >= "12:00":
            return False, f"Sai khung giờ: yêu cầu buổi sáng (<12:00), chuyến bay lúc {flight.depart_time}"

        if self.criteria.preferred_time == "afternoon" and not ("12:00" <= flight.depart_time < "18:00"):
            return False, f"Sai khung giờ: yêu cầu buổi chiều (12:00-18:00), chuyến bay lúc {flight.depart_time}"

        if self.criteria.preferred_time == "evening" and flight.depart_time < "18:00":
            return False, f"Sai khung giờ: yêu cầu buổi tối (>=18:00), chuyến bay lúc {flight.depart_time}"

        return True, "Thỏa mãn tất cả ràng buộc dữ liệu."

    def calculate_progress_metric(self, context: Dict[str, Any]) -> int:
        """
        Tính toán đại lượng tiến triển (progress metric) khách quan cho LoopDetector.
        0: Chưa tìm kiếm chuyến bay
        1: Đã tìm kiếm và có danh sách chuyến bay
        2: Đã kiểm tra chi tiết ghế trống cho chuyến phù hợp
        3: Đã giữ chỗ thành công (status='held')
        4: Đã thanh toán và xuất vé thành công (status='confirmed', paid=True)
        """
        score = 0
        if context.get("flights_found"):
            score = max(score, 1)
        if context.get("selected_flight"):
            score = max(score, 2)
        if context.get("held_booking_id"):
            score = max(score, 3)
        if context.get("booking_confirmed"):
            score = max(score, 4)
        return score
