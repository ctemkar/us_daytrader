import math
class SignalEngine:
    def __init__(self, buy_threshold=-1.0, sell_threshold=1.0):
        self.buy_threshold = float(buy_threshold)
        self.sell_threshold = float(sell_threshold)
    def evaluate(self, stats):
        if not stats or "pc" not in stats:
            return "HOLD", 0.0, "no data"
        pc = float(stats.get("pc", 0.0))
        if pc <= self.buy_threshold:
            return "BUY", min(1.0, abs(pc) / 2.0), f"pc {pc} <= buy_threshold {self.buy_threshold}"
        if pc >= self.sell_threshold:
            return "SELL", min(1.0, abs(pc) / 2.0), f"pc {pc} >= sell_threshold {self.sell_threshold}"
        return "HOLD", max(0.0, 1.0 - abs(pc) / 2.0), f"pc {pc} within thresholds"
