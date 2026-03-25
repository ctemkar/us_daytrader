import json
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

POSITIONS_FILE = Path("paper_positions.json")

class PaperClient:
    def __init__(self):
        self._positions = {}
        self._load()
    def _load(self):
        try:
            if POSITIONS_FILE.exists():
                self._positions = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
            else:
                self._positions = {}
        except Exception as e:
            logging.error("paper load error %s", e)
            self._positions = {}
    def _save(self):
        try:
            POSITIONS_FILE.write_text(json.dumps(self._positions), encoding="utf-8")
        except Exception as e:
            logging.error("paper save error %s", e)
    def create_order(self, symbol, qty, side, order_type="market", time_in_force="day", short=False):
        ts = int(time.time())
        qty = int(qty)
        side = side.lower()
        cur = int(self._positions.get(symbol, 0))
        if side == "buy":
            new = cur + qty
        else:
            if short:
                new = cur - qty
            else:
                new = cur - qty
        self._positions[symbol] = new
        self._save()
        return {"status": "filled", "symbol": symbol, "side": side, "qty": qty, "position": new, "ts": ts}
    def get_position_qty(self, symbol):
        return int(self._positions.get(symbol, 0))
    def get_positions(self):
        return {k: int(v) for k, v in self._positions.items() if int(v) != 0}
    def close_all(self):
        res = []
        for s, q in list(self._positions.items()):
            if int(q) == 0:
                continue
            side = "sell" if int(q) > 0 else "buy"
            qty = abs(int(q))
            res.append(self.create_order(symbol=s, qty=qty, side=side, order_type="market", time_in_force="day", short=False))
        return res
