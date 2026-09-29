import sys
import io
import json

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from flight_booking.models import FlightCriteria
from flight_booking.mock_tools import reset_db
from flight_booking.harness.harness_runner import AgentHarness
from flight_booking.agents.react_agent import ReActAgent
from flight_booking.agents.plan_execute_agent import PlanThenExecuteAgent
from flight_booking.agents.hybrid_agent import HybridAgent


def run_interactive_demo():
    print("=" * 50)
    print("   HỆ THỐNG ĐẶT VÉ MÁY BAY AGENTIC AI   ")
    print("=" * 50)
    print("Mô hình hỗ trợ 3 mẫu thiết kế:")
    print("1. ReAct Agent ")
    print("2. Plan-then-Execute Agent ")
    print("3. Hybrid Agent ")
    print("-" * 50)

    # Tiêu chí đặt vé mẫu
    criteria = FlightCriteria(
        origin="SGN",
        destination="DAD",
        depart_date="2026-10-07",
        passenger_name="Vo Van Hai",
        max_price=2000000.0,
        preferred_time="morning"
    )

    query = "Đặt giúp tôi vé máy bay từ SGN đi DAD vào sáng ngày 2026-10-07 cho Vo Van Hai, ngân sách tối đa 2 triệu."

    print(f"Tiêu chí: {criteria.origin} -> {criteria.destination} | Ngày: {criteria.depart_date} | Ngân sách: {criteria.max_price:,.0f}đ")
    print(f"Yêu cầu người dùng: '{query}'\n")

    agents = [
        ("ReAct Agent", ReActAgent),
        ("Plan-then-Execute Agent", PlanThenExecuteAgent),
        ("Hybrid Agent", HybridAgent)
    ]

    for name, agent_cls in agents:
        reset_db()
        print("*" * 50)
        print(f"ĐANG THỰC THI: {name}")
        print("*" * 50)

        harness = AgentHarness(
            criteria=criteria,
            max_steps=8,
            require_approval_for_pay=True,
            auto_approve=True
        )

        agent = agent_cls(harness)
        result = agent.run(query)

        print("\n--- KẾT QUẢ THỰC THI ---")
        print(f"- Trạng thái thành công: {result.success}")
        print(f"- Lý do dừng: {result.termination_reason}")
        print(f"- Mã đặt vé: {result.booking_id}")
        print(f"- Số bước công cụ: {result.steps_count}")
        print(f"- Số lần gọi LLM: {result.llm_call_count}")
        print(f"- Thời gian thực thi: {result.duration_sec}s")

        print("\n--- NHẬT KÝ VẾT TỪNG BƯỚC CỦA HARNESS ---")
        for trace in result.history:
            print(f"  [Bước {trace['step']}] Gọi Tool: {trace['tool']}")
            print(f"     Tham số: {trace['args']}")
            obs_preview = str(trace['observation'])
            if len(obs_preview) > 120:
                obs_preview = obs_preview[:120] + "..."
            print(f"     Kết quả: {obs_preview}")
            print(f"     Trạng thái Harness: {trace['status']}\n")

        if result.handoff_ticket:
            print("--- PHIẾU BÀN GIAO ---")
            print(json.dumps(result.handoff_ticket.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_interactive_demo()
