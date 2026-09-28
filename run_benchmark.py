"""
CLI Benchmark Runner: Chạy toàn diện 5 kịch bản trên 3 kiến trúc Agent
và xuất dữ liệu thực nghiệm cho Báo cáo Đánh giá (report_evaluation.md).
"""

import time
import os
import sys
import io
import json

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from flight_booking.benchmark.evaluator import BenchmarkEvaluator
from flight_booking.benchmark.test_scenarios import get_all_scenarios


def main():
    print("=" * 80)
    print("   CHƯƠNG TRÌNH BENCHMARK ĐÁNH GIÁ HIỆU NĂNG AGENTIC AI (SE373 - BTVN#3)   ")
    print("=" * 80)

    evaluator = BenchmarkEvaluator(get_all_scenarios())
    results = evaluator.run_all(["ReActAgent", "PlanThenExecuteAgent", "HybridAgent"])

    summary_md = evaluator.generate_summary_report()
    print("\n" + "=" * 80)
    print("KẾT QUẢ ĐÁNH GIÁ TỔNG QUAN:")
    print("=" * 80)
    print(summary_md)

    # Lưu kết quả thô dạng JSON
    raw_results = [r.model_dump() for r in results]
    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(raw_results, f, ensure_ascii=False, indent=2)
    print("\n[OK] Đã lưu dữ liệu thô vào 'benchmark_results.json'.")


if __name__ == "__main__":
    main()
