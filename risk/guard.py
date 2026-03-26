import logging
from config.settings import MAX_POSITIONS, TRADING_END_EST

class RiskGuard:
    def __init__(self):
        self.max_positions = MAX_POSITIONS
        logging.info(f"RiskGuard initialized. Max: {self.max_positions}. Cutoff: {TRADING_END_EST}")

    def can_enter_new_position(self, current_count):
        return current_count < self.max_positions
