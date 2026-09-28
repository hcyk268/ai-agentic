"""
Bộ phát hiện lặp và bế tắc (Loop & Stall Detector).
Trích nguyên mẫu kiến trúc từ Slide 46 của SE373.
"""

from collections import deque
from typing import Dict, Any, Optional, Literal


class LoopDetector:
    """
    Theo dõi chuỗi hành động và đại lượng tiến triển (progress).
    - LOOP: (tool, args) xuất hiện lặp lại >= k lần trong cửa sổ trượt (window).
    - STALL: Đại lượng tiến triển không thay đổi liên tiếp >= n vòng.
    """

    def __init__(self, window: int = 6, repeat_k: int = 2, stall_n: int = 4):
        self.recent = deque(maxlen=window)  # Chỉ so cửa sổ gần
        self.k = repeat_k
        self.n = stall_n
        self.last = None
        self.stall = 0

    def check(self, tool: str, args: Dict[str, Any], progress: int) -> Optional[Literal["LOOP", "STALL"]]:
        """
        Kiểm tra dấu hiệu bất thường sau mỗi lần model đề xuất gọi tool.
        """
        # Polling ngoại lệ: get_booking tra cứu trạng thái có thể được gọi nhiều lần hợp lệ nếu đang chờ
        # nhưng nếu trùng hoàn toàn tham số khi không có trạng thái bất đồng bộ thì vẫn xem xét
        fp = (tool, repr(sorted(args.items())))

        if self.recent.count(fp) + 1 >= self.k:
            return "LOOP"

        self.recent.append(fp)

        if self.last is not None and progress == self.last:
            self.stall += 1
        else:
            self.stall = 0

        self.last = progress

        if self.stall >= self.n:
            return "STALL"

        return None
