from collections import deque
from typing import Dict, Any, Optional, Literal


class LoopDetector:
    def __init__(self, window: int = 6, repeat_k: int = 2, stall_n: int = 4):
        self.recent = deque(maxlen=window)
        self.k = repeat_k
        self.n = stall_n
        self.last = None
        self.stall = 0

    def check(self, tool: str, args: Dict[str, Any], progress: int) -> Optional[Literal["LOOP", "STALL"]]:
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
