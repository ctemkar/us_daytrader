class RiskGuard:
    def __init__(self, max_position_size=10000):
        self.max_position_size = max_position_size
        self.positions = {}

    def validate(self, symbol, decision, price):
        if decision not in ["BUY", "SELL"]:
            return False
        current_pos = self.positions.get(symbol, 0)
        if decision == "BUY":
            if current_pos * price >= self.max_position_size:
                return False
            self.positions[symbol] = current_pos + 1
            return True
        if decision == "SELL":
            if current_pos <= 0:
                return False
            self.positions[symbol] = current_pos - 1
            return True
        return False
