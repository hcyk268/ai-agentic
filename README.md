# Hệ Thống AI Agent Đặt Vé Máy Bay (SE373 - BTVN#3)

> Hệ thống Agentic AI đặt vé máy bay xây dựng bằng LangChain, LangGraph và khung Harness bảo vệ toàn diện theo bài giảng SE373 (Buổi 03: *Agent Fundamentals*).

---

## Cấu trúc thư mục

```
ai-agentic/
├── requirements.txt                  # Các thư viện phụ thuộc (LangChain, LangGraph, OpenAI, Pydantic, Pytest)
├── .env                              # Cấu hình API key và Endpoint mô hình
├── report_evaluation.md              # Báo cáo đánh giá hiệu năng và so sánh 3 mẫu thiết kế (.md)
├── benchmark_results.json            # Dữ liệu thực nghiệm benchmark thô
├── run_demo.py                       # Script chạy demo trực quan 3 mẫu thiết kế và các chặng Harness
├── run_benchmark.py                  # Script chạy đánh giá benchmark định lượng trên 5 kịch bản
├── flight_booking/
│   ├── __init__.py
│   ├── models.py                     # Pydantic schemas (FlightCriteria, Flight, BookingRecord, HandoffTicket, ToolResult)
│   ├── mock_tools.py                 # Mock tools (search_flights, check_seat, book_seat, pay, get_booking)
│   ├── llm.py                        # Helper kết nối LLM qua ChatOpenAI
│   ├── harness/
│   │   ├── __init__.py
│   │   ├── constraints.py            # Lớp 1: Ràng buộc là dữ liệu (Data Constraints)
│   │   ├── completion.py             # Lớp 2: Tiêu chí hoàn thành kiểm bằng code (Sensor Computational)
│   │   ├── permissions.py            # Lớp 3: Kiểm quyền trước khi gọi tool (Permission Gate)
│   │   ├── handoff.py                # Lớp 4: Bàn giao cho con người (30s Handoff Ticket)
│   │   ├── loop_detector.py          # Bộ phát hiện lặp và bế tắc (Loop & Stall Detector)
│   │   └── harness_runner.py         # Sơ đồ trục Vòng lặp Agent và Checklist 5 điều kiện dừng
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── react_agent.py            # Mẫu 1: ReAct Agent (Thought -> Act -> Observe)
│   │   ├── plan_execute_agent.py     # Mẫu 2: Plan-then-Execute Agent (Lập kế hoạch trước -> Thực thi)
│   │   └── hybrid_agent.py           # Mẫu 3: Mẫu Lai (Plan + ReAct + Dynamic Replanning)
│   └── benchmark/
│       ├── __init__.py
│       ├── test_scenarios.py         # 5 Kịch bản đánh giá (Tiêu chuẩn, Hết chỗ, Ngân sách chặt, Kiểm quyền, Lỗi)
│       └── evaluator.py              # Bộ điều phối thu thập số liệu và tổng hợp báo cáo
└── tests/
    ├── test_tools.py                 # Unit tests cho mock tools
    ├── test_harness.py               # Unit tests cho đủ 4 lớp Harness và Loop detector
    └── test_agents.py                # Integration tests tích hợp end-to-end cho 3 agent và cổng kiểm quyền
```

---

## Hướng dẫn cài đặt & Thực thi

### 1. Cài đặt môi trường
```bash
pip install -r requirements.txt
```

### 2. Chạy toàn bộ Test Suite (16/16 Passed)
```bash
python -m pytest tests/ -v
```

### 3. Chạy Demo minh họa
```bash
python run_demo.py
```

### 4. Chạy Benchmark đánh giá định lượng
```bash
python run_benchmark.py
```

Báo cáo phân tích chi tiết xem tại [report_evaluation.md](file:///D:/a2024START/agentic/ai-agentic/report_evaluation.md).
