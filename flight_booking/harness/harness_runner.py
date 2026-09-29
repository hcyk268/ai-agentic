import time
from typing import Dict, Any, List, Optional, Tuple, Callable
from flight_booking.models import FlightCriteria, HandoffTicket, AgentRunResult
from flight_booking.harness.constraints import DataConstraintManager
from flight_booking.harness.completion import CompletionVerifier
from flight_booking.harness.permissions import PermissionManager
from flight_booking.harness.loop_detector import LoopDetector
from flight_booking.harness.handoff import HandoffManager
from flight_booking.mock_tools import get_db, FLIGHT_TOOLS


class AgentHarness:
    """
    Khung Harness bảo vệ và giám sát Agent:
    - Quản lý dữ liệu bất biến
    - Kiểm quyền thực thi trước mỗi tool call
    - Kiểm tra tiêu chí hoàn thành
    - Phát hiện lặp
    - Phát hiện bế tắc
    - Giới hạn ngân sách
    - Phát sinh phiếu bàn giao
    """

    def __init__(
        self,
        criteria: FlightCriteria,
        max_steps: int = 10,
        timeout_sec: float = 60.0,
        require_approval_for_pay: bool = True,
        require_approval_for_non_refundable: bool = True,
        approval_price_threshold: float = 1500000.0,
        auto_approve: bool = False
    ):
        self.criteria = criteria
        self.max_steps = max_steps
        self.timeout_sec = timeout_sec

        self.constraint_mgr = DataConstraintManager(criteria)
        self.completion_verifier = CompletionVerifier(criteria)
        self.permission_mgr = PermissionManager(
            criteria=criteria,
            require_approval_for_pay=require_approval_for_pay,
            require_approval_for_non_refundable=require_approval_for_non_refundable,
            approval_price_threshold=approval_price_threshold,
            auto_approve=auto_approve
        )
        self.loop_detector = LoopDetector(window=6, repeat_k=2, stall_n=4)

        self.context: Dict[str, Any] = {
            "flights_found": False,
            "selected_flight": None,
            "held_booking_id": None,
            "booking_confirmed": False,
            "failed_attempts": [],
            "last_flight_id": None
        }

        self.step_count = 0
        self.llm_call_count = 0
        self.start_time = 0.0
        self.history_trace: List[Dict[str, Any]] = []

        self.tool_map = {t.name: t for t in FLIGHT_TOOLS}

    def start_session(self):
        self.start_time = time.time()
        self.step_count = 0
        self.llm_call_count = 0
        self.history_trace.clear()

    def build_system_context(self) -> str:
        return (
            "BẠN LÀ TRỢ LÝ ĐẶT VÉ MÁY BAY CHUYÊN NGHIỆP.\n"
            "=== RÀNG BUỘC BẮT BUỘC TỪ HỆ THỐNG ===\n"
            f"- Điểm đi: {self.criteria.origin}\n"
            f"- Điểm đến: {self.criteria.destination}\n"
            f"- Ngày bay: {self.criteria.depart_date}\n"
            f"- Tên hành khách: {self.criteria.passenger_name}\n"
            f"- Ngân sách tối đa: {self.criteria.max_price:,.0f} VNĐ\n"
            f"- Khung giờ ưu tiên: {self.criteria.preferred_time}\n"
            "==========================================================\n"
            "QUY TẮC AN TOÀN VÀ VẬN HÀNH:\n"
            "1. Chỉ dùng các tool được cung cấp để tra cứu và đặt vé. Tuyệt đối không bịa đặt mã chuyến bay hoặc giá.\n"
            "2. Khi nhận kết quả từ tool dạng JSON, đọc kỹ trường status và dữ liệu.\n"
            "3. Quy trình chuẩn: Tìm chuyến bay -> Kiểm tra ghế và giá -> Giữ chỗ -> Thanh toán.\n"
            "4. Tuyệt đối không chọn vé vượt ngân sách tối đa hoặc sai ngày/tuyến đường.\n"
        )

    def execute_tool_with_harness(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Optional[str], Optional[HandoffTicket]]:
        """
        Thực thi tool qua chu trình kiểm duyệt của Harness:
        - #0: Kiểm quyền trước khi gọi.
        - #1 -> #4: Kiểm tra điều kiện dừng sau khi có observation.
        Trả về: (observation_dict, termination_reason, handoff_ticket)
        """
        self.step_count += 1
        current_step = self.step_count

        # ---------------
        # #0: KIỂM QUYỀN
        # ---------------
        allowed, approval_req = self.permission_mgr.check_tool_permission(
            tool_name=tool_name,
            args=tool_args,
            context=self.context
        )

        if not allowed and approval_req:
            handoff = HandoffManager.create_permission_handoff(
                criteria=self.criteria,
                action=approval_req.action,
                params=approval_req.params,
                reason=approval_req.reason,
                context=self.context
            )
            self._log_trace(current_step, tool_name, tool_args, {"error": "Cần phê duyệt quyền"}, "NEEDS_APPROVAL")
            return {"status": "pending_approval", "message": approval_req.reason}, "NEEDS_APPROVAL", handoff

        target_tool = self.tool_map.get(tool_name)
        if not target_tool:
            obs = {"status": "error", "message": f"Công cụ '{tool_name}' không tồn tại trong danh mục."}
            self.context["failed_attempts"].append(f"Gọi sai tên công cụ '{tool_name}'")
        else:
            try:
                obs = target_tool.invoke(tool_args)
            except Exception as e:
                obs = {"status": "error", "message": f"Lỗi thực thi công cụ: {str(e)}"}
                self.context["failed_attempts"].append(f"Tool {tool_name} gặp lỗi ngoại lệ: {str(e)}")

        self._update_internal_context(tool_name, tool_args, obs)

        progress = self.constraint_mgr.calculate_progress_metric(self.context)

        # -------------------------
        # #1: TIÊU CHÍ HOÀN THÀNH
        # -------------------------
        booking_id = self.context.get("held_booking_id")
        verified, msg, details = self.completion_verifier.verify_booking(booking_id)
        if verified:
            self._log_trace(current_step, tool_name, tool_args, obs, "GOAL_ACHIEVED")
            return obs, "GOAL_ACHIEVED", None

        # -------------------
        # #2: PHÁT HIỆN LẶP
        # -------------------
        loop_status = self.loop_detector.check(tool_name, tool_args, progress)
        if loop_status == "LOOP":
            handoff = HandoffManager.create_loop_or_stall_handoff("LOOP", self.context, self.criteria, f"Gọi trùng lặp {tool_name}")
            self._log_trace(current_step, tool_name, tool_args, obs, "LOOP_DETECTED")
            return obs, "LOOP_DETECTED", handoff

        # ----------------------
        # #3: PHÁT HIỆN BẾ TẮC
        # ----------------------
        if loop_status == "STALL":
            handoff = HandoffManager.create_loop_or_stall_handoff("STALL", self.context, self.criteria, "Không có tiến triển qua nhiều vòng")
            self._log_trace(current_step, tool_name, tool_args, obs, "STALL_DETECTED")
            return obs, "STALL_DETECTED", handoff

        # ---------------
        # #4: NGÂN SÁCH
        # ---------------
        elapsed = time.time() - self.start_time
        if self.step_count >= self.max_steps or elapsed >= self.timeout_sec:
            handoff = HandoffManager.create_budget_exhausted_handoff(self.context, self.criteria, self.max_steps)
            self._log_trace(current_step, tool_name, tool_args, obs, "BUDGET_EXHAUSTED")
            return obs, "BUDGET_EXHAUSTED", handoff

        # Tiếp tục vòng lặp
        self._log_trace(current_step, tool_name, tool_args, obs, "CONTINUE")
        return obs, None, None

    def _update_internal_context(self, tool_name: str, args: Dict[str, Any], obs: Dict[str, Any]):
        status = obs.get("status") if isinstance(obs, dict) else None

        if tool_name == "search_flights":
            if status == "success" and obs.get("data"):
                self.context["flights_found"] = True
            elif status in ("not_found", "error"):
                self.context["failed_attempts"].append(f"Tìm chuyến {args}: {obs.get('message')}")

        elif tool_name == "check_seat":
            if status == "success":
                self.context["selected_flight"] = args.get("flight_id")
                self.context["last_flight_id"] = args.get("flight_id")
            elif status in ("sold_out", "not_found"):
                self.context["failed_attempts"].append(f"Kiểm tra ghế {args.get('flight_id')}: {obs.get('message')}")

        elif tool_name == "book_seat":
            if status == "success":
                booking_data = obs.get("data", {})
                self.context["held_booking_id"] = booking_data.get("booking_id")
            else:
                self.context["failed_attempts"].append(f"Đặt chỗ {args}: {obs.get('message')}")

        elif tool_name == "pay":
            if status == "success":
                self.context["booking_confirmed"] = True
            else:
                self.context["failed_attempts"].append(f"Thanh toán {args}: {obs.get('message')}")

    def _log_trace(self, step: int, tool: str, args: Dict[str, Any], obs: Any, status: str):
        self.history_trace.append({
            "step": step,
            "tool": tool,
            "args": args,
            "observation": obs,
            "status": status,
            "timestamp": time.time()
        })

    def final_verification(self) -> Tuple[bool, str]:
        booking_id = self.context.get("held_booking_id")
        return self.completion_verifier.verify_booking(booking_id)[:2]
