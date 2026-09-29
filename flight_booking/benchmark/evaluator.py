import time
from typing import List, Dict, Any, Optional
from flight_booking.models import AgentRunResult
from flight_booking.mock_tools import reset_db
from flight_booking.harness.harness_runner import AgentHarness
from flight_booking.agents.react_agent import ReActAgent
from flight_booking.agents.plan_execute_agent import PlanThenExecuteAgent
from flight_booking.agents.hybrid_agent import HybridAgent
from flight_booking.benchmark.test_scenarios import Scenario, get_all_scenarios


class BenchmarkEvaluator:
    def __init__(self, scenarios: Optional[List[Scenario]] = None):
        self.scenarios = scenarios or get_all_scenarios()
        self.results: List[AgentRunResult] = []

    def run_all(self, selected_agents: Optional[List[str]] = None) -> List[AgentRunResult]:
        agent_names = selected_agents or ["ReActAgent", "PlanThenExecuteAgent", "HybridAgent"]
        self.results.clear()

        print("=" * 80)
        print("BẮT ĐẦU ĐÁNH GIÁ BENCHMARK 3 MẪU THIẾT KẾ AGENT")
        print("=" * 80)

        for sc in self.scenarios:
            print(f"\n>>> [KỊCH BẢN]: {sc.name} ({sc.scenario_id})")
            print(f"    Mục tiêu: {sc.description}")

            for a_name in agent_names:
                reset_db()

                settings = sc.harness_settings.copy()
                harness = AgentHarness(
                    criteria=sc.criteria,
                    max_steps=settings.get("max_steps", 8),
                    timeout_sec=settings.get("timeout_sec", 60.0),
                    require_approval_for_pay=settings.get("require_approval_for_pay", False),
                    require_approval_for_non_refundable=settings.get("require_approval_for_non_refundable", False),
                    auto_approve=settings.get("auto_approve", True)
                )

                if a_name == "ReActAgent":
                    agent = ReActAgent(harness)
                elif a_name == "PlanThenExecuteAgent":
                    agent = PlanThenExecuteAgent(harness)
                elif a_name == "HybridAgent":
                    agent = HybridAgent(harness)
                else:
                    continue

                print(f"    - Đang chạy {a_name}...", end=" ", flush=True)
                run_res = agent.run(sc.user_query)
                self.results.append(run_res)

                status_str = "THÀNH CÔNG" if run_res.success else f"KẾT THÚC ({run_res.termination_reason})"
                print(f"{status_str} | Bước: {run_res.steps_count} | LLM calls: {run_res.llm_call_count} | Thời gian: {run_res.duration_sec}s")

        return self.results

    def generate_summary_report(self) -> str:
        if not self.results:
            return "Chưa có kết quả benchmark nào."

        stats: Dict[str, Dict[str, Any]] = {}
        for r in self.results:
            if r.agent_name not in stats:
                stats[r.agent_name] = {
                    "total": 0,
                    "success": 0,
                    "steps": [],
                    "llm_calls": [],
                    "durations": [],
                    "terminations": {}
                }
            s = stats[r.agent_name]
            s["total"] += 1
            if r.success:
                s["success"] += 1
            s["steps"].append(r.steps_count)
            s["llm_calls"].append(r.llm_call_count)
            s["durations"].append(r.duration_sec)
            s["terminations"][r.termination_reason] = s["terminations"].get(r.termination_reason, 0) + 1

        md = []
        md.append("## BẢNG SO SÁNH TỔNG HỢP HIỆU NĂNG 3 MẪU THIẾT KẾ AGENT\n")
        md.append("| Chỉ số đánh giá | ReAct Agent | Plan-then-Execute | Mẫu Lai (Hybrid) |")
        md.append("| :--- | :---: | :---: | :---: |")

        def avg(lst):
            return round(sum(lst) / len(lst), 2) if lst else 0.0

        react = stats.get("ReActAgent", {})
        plan = stats.get("PlanThenExecuteAgent", {})
        hybrid = stats.get("HybridAgent", {})

        r_sr = f"{(react.get('success', 0)/react.get('total', 1)*100):.1f}%" if react else "N/A"
        p_sr = f"{(plan.get('success', 0)/plan.get('total', 1)*100):.1f}%" if plan else "N/A"
        h_sr = f"{(hybrid.get('success', 0)/hybrid.get('total', 1)*100):.1f}%" if hybrid else "N/A"
        md.append(f"| **Tỷ lệ thành công (Code verified)** | **{r_sr}** | {p_sr} | **{h_sr}** |")

        md.append(f"| **Số bước gọi Tool (Avg Steps)** | {avg(react.get('steps', []))} | {avg(plan.get('steps', []))} | {avg(hybrid.get('steps', []))} |")

        md.append(f"| **Số lần gọi LLM (Avg LLM calls)** | {avg(react.get('llm_calls', []))} | {avg(plan.get('llm_calls', []))} | {avg(hybrid.get('llm_calls', []))} |")

        md.append(f"| **Thời gian trung bình (Giây)** | {avg(react.get('durations', []))}s | {avg(plan.get('durations', []))}s | {avg(hybrid.get('durations', []))}s |")

        md.append("\n### BẢNG CHI TIẾT THEO TỪNG KỊCH BẢN\n")
        md.append("| Kịch bản | Agent | Kết quả | Lý do kết thúc | Bước | LLM Calls | Thời gian |")
        md.append("| :--- | :--- | :---: | :--- | :---: | :---: | :---: |")

        for r in self.results:
            res_icon = "✅ Thành công" if r.success else "⚠️ Dừng an toàn"
            md.append(f"| {r.scenario_id} | {r.agent_name} | {res_icon} | `{r.termination_reason}` | {r.steps_count} | {r.llm_call_count} | {r.duration_sec}s |")

        return "\n".join(md)
