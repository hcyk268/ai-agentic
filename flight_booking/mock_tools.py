"""
Mock flight booking tools.
"""

from typing import Dict, Any, List, Optional
import uuid
from langchain_core.tools import tool
from flight_booking.models import Flight, BookingRecord, ToolResult


class MockFlightDatabase:
    """Mock in-memory database."""
    def __init__(self):
        self.flights: Dict[str, Flight] = {}
        self.bookings: Dict[str, BookingRecord] = {}
        self.init_data()

    def init_data(self):
        self.bookings.clear()
        sample_flights = [
            Flight(
                flight_id="VN122",
                airline="Vietnam Airlines",
                origin="SGN",
                destination="DAD",
                depart_date="2026-10-07",
                depart_time="08:30",
                price=1850000.0,
                available_seats=["12A", "12B", "14C"],
                refundable=False,
                seat_class="Economy"
            ),
            Flight(
                flight_id="VJ604",
                airline="Vietjet Air",
                origin="SGN",
                destination="DAD",
                depart_date="2026-10-07",
                depart_time="09:15",
                price=1450000.0,
                available_seats=["05A", "05B", "06C", "07D"],
                refundable=True,
                seat_class="Economy"
            ),
            Flight(
                flight_id="QH118",
                airline="Bamboo Airways",
                origin="SGN",
                destination="DAD",
                depart_date="2026-10-07",
                depart_time="14:00",
                price=2200000.0,
                available_seats=["02A", "02C"],
                refundable=True,
                seat_class="Premium Economy"
            ),
            Flight(
                flight_id="VN134",
                airline="Vietnam Airlines",
                origin="SGN",
                destination="DAD",
                depart_date="2026-10-07",
                depart_time="11:00",
                price=1900000.0,
                available_seats=[],  # Chuyến đã hết ghế (để test fallback / loop detection)
                refundable=True,
                seat_class="Economy"
            ),
            Flight(
                flight_id="VN210",
                airline="Vietnam Airlines",
                origin="SGN",
                destination="HAN",
                depart_date="2026-10-08",
                depart_time="07:00",
                price=2100000.0,
                available_seats=["10A", "10B", "11A"],
                refundable=True,
                seat_class="Economy"
            ),
            Flight(
                flight_id="VJ180",
                airline="Vietjet Air",
                origin="HAN",
                destination="DAD",
                depart_date="2026-10-09",
                depart_time="15:30",
                price=1350000.0,
                available_seats=["18A", "18B"],
                refundable=False,
                seat_class="Economy"
            ),
        ]
        self.flights = {f.flight_id: f for f in sample_flights}


# Singleton database instance
_DB = MockFlightDatabase()


def get_db() -> MockFlightDatabase:
    return _DB


def reset_db():
    _DB.init_data()



@tool
def search_flights(origin: str, destination: str, depart_date: str) -> Dict[str, Any]:
    """
    Tìm kiếm danh sách chuyến bay khả dụng theo sân bay đi, sân bay đến và ngày khởi hành.
    Tham số:
    - origin: Mã IATA sân bay đi (VD: SGN, HAN, DAD)
    - destination: Mã IATA sân bay đến (VD: SGN, HAN, DAD)
    - depart_date: Ngày bay định dạng YYYY-MM-DD
    """
    origin = origin.strip().upper()
    destination = destination.strip().upper()
    depart_date = depart_date.strip()

    valid_airports = {"SGN", "HAN", "DAD", "HUI", "CXR", "PQC"}
    if origin not in valid_airports or destination not in valid_airports:
        return ToolResult(
            status="error",
            message=f"Mã sân bay không hợp lệ. Chỉ hỗ trợ các sân bay: {sorted(list(valid_airports))}",
            hint="Vui lòng kiểm tra lại mã sân bay đi/đến (VD: SGN, HAN, DAD)"
        ).model_dump()

    matched = [
        f.model_dump()
        for f in _DB.flights.values()
        if f.origin == origin and f.destination == destination and f.depart_date == depart_date
    ]

    if not matched:
        return ToolResult(
            status="not_found",
            message=f"Không tìm thấy chuyến bay nào từ {origin} đi {destination} vào ngày {depart_date}.",
            hint="Thử tìm chuyến bay sang ngày lân cận hoặc kiểm tra lại tuyến đường.",
            data=[]
        ).model_dump()

    return ToolResult(
        status="success",
        message=f"Tìm thấy {len(matched)} chuyến bay phù hợp.",
        data=matched
    ).model_dump()


@tool
def check_seat(flight_id: str) -> Dict[str, Any]:
    """
    Kiểm tra tình trạng ghế trống, mức giá và chính sách hoàn hủy của một chuyến bay cụ thể.
    Tham số:
    - flight_id: Mã chuyến bay (VD: VN122, VJ604)
    """
    flight_id = flight_id.strip().upper()
    flight = _DB.flights.get(flight_id)

    if not flight:
        return ToolResult(
            status="not_found",
            message=f"Chuyến bay mã '{flight_id}' không tồn tại trong hệ thống.",
            hint="Gọi search_flights để lấy danh sách mã chuyến bay hợp lệ."
        ).model_dump()

    if not flight.available_seats:
        return ToolResult(
            status="sold_out",
            message=f"Chuyến bay '{flight_id}' hiện đã hết chỗ.",
            hint="Vui lòng kiểm tra chuyến bay khác cùng hành trình.",
            data={"flight_id": flight_id, "available_seats": []}
        ).model_dump()

    return ToolResult(
        status="success",
        message=f"Chuyến bay {flight_id} còn {len(flight.available_seats)} ghế trống.",
        data={
            "flight_id": flight.flight_id,
            "airline": flight.airline,
            "origin": flight.origin,
            "destination": flight.destination,
            "depart_date": flight.depart_date,
            "depart_time": flight.depart_time,
            "price": flight.price,
            "refundable": flight.refundable,
            "available_seats": flight.available_seats,
            "seat_class": flight.seat_class
        }
    ).model_dump()


@tool
def book_seat(flight_id: str, seat_number: str, passenger_name: str) -> Dict[str, Any]:
    """
    Đặt giữ chỗ trên chuyến bay. Hành động này sẽ khóa ghế tạm thời (status='held').
    Tham số:
    - flight_id: Mã chuyến bay
    - seat_number: Vị trí ghế muốn chọn (VD: 12A)
    - passenger_name: Họ tên hành khách
    """
    flight_id = flight_id.strip().upper()
    seat_number = seat_number.strip().upper()
    passenger_name = passenger_name.strip()

    flight = _DB.flights.get(flight_id)
    if not flight:
        return ToolResult(
            status="not_found",
            message=f"Chuyến bay {flight_id} không tồn tại.",
            hint="Kiểm tra lại mã chuyến bay qua search_flights."
        ).model_dump()

    if seat_number not in flight.available_seats:
        return ToolResult(
            status="error",
            message=f"Ghế {seat_number} không còn trống hoặc không tồn tại trên chuyến {flight_id}.",
            hint=f"Các ghế đang còn trống: {flight.available_seats}",
            data={"available_seats": flight.available_seats}
        ).model_dump()

    flight.available_seats.remove(seat_number)
    booking_id = f"BK-{flight_id}-{seat_number}-{uuid.uuid4().hex[:4].upper()}"

    record = BookingRecord(
        booking_id=booking_id,
        flight_id=flight_id,
        passenger_name=passenger_name,
        seat_number=seat_number,
        price=flight.price,
        status="held",
        paid=False,
        refundable=flight.refundable
    )
    _DB.bookings[booking_id] = record

    return ToolResult(
        status="success",
        message=f"Đã giữ chỗ thành công mã {booking_id}. Ghế {seat_number} chuyến {flight_id}.",
        data=record.model_dump()
    ).model_dump()


@tool
def pay(booking_id: str, payment_method: str = "corp_card", amount: Optional[float] = None) -> Dict[str, Any]:
    """
    Thanh toán cho vé đã giữ chỗ để chuyển sang trạng thái đã xuất vé (confirmed).
    Tham số:
    - booking_id: Mã giữ chỗ (VD: BK-VN122-12A-ABCD)
    - payment_method: Phương thức thanh toán (corp_card, personal_card)
    - amount: Số tiền thanh toán (nếu None sẽ thanh toán đúng giá vé)
    """
    booking_id = booking_id.strip()
    booking = _DB.bookings.get(booking_id)

    if not booking:
        return ToolResult(
            status="not_found",
            message=f"Không tìm thấy mã giữ chỗ '{booking_id}'.",
            hint="Vui lòng gọi book_seat trước khi gọi pay."
        ).model_dump()

    if booking.status == "confirmed" and booking.paid:
        return ToolResult(
            status="success",
            message=f"Mã đặt chỗ '{booking_id}' đã được thanh toán trước đó.",
            data=booking.model_dump()
        ).model_dump()

    if amount is not None and amount < booking.price:
        return ToolResult(
            status="error",
            message=f"Số tiền thanh toán {amount:,.0f}đ không đủ cho giá vé {booking.price:,.0f}đ.",
            hint="Vui lòng truyền đúng số tiền vé."
        ).model_dump()

    booking.status = "confirmed"
    booking.paid = True

    return ToolResult(
        status="success",
        message=f"Thanh toán thành công {booking.price:,.0f}đ bằng {payment_method}. Vé đã được xuất (confirmed).",
        data=booking.model_dump()
    ).model_dump()


@tool
def get_booking(booking_id: str) -> Dict[str, Any]:
    """
    Tra cứu chi tiết tình trạng đặt chỗ từ hệ thống vé máy bay.
    Tham số:
    - booking_id: Mã đặt chỗ cần tra cứu
    """
    booking_id = booking_id.strip()
    booking = _DB.bookings.get(booking_id)

    if not booking:
        return ToolResult(
            status="not_found",
            message=f"Mã vé '{booking_id}' không tồn tại trong hệ thống.",
            hint="Kiểm tra lại mã vé hoặc gọi book_seat."
        ).model_dump()

    return ToolResult(
        status="success",
        message="Tra cứu mã đặt chỗ thành công.",
        data=booking.model_dump()
    ).model_dump()


# Danh sách các tools
FLIGHT_TOOLS = [search_flights, check_seat, book_seat, pay, get_booking]
