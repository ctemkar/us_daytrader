import datetime
import pytz
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

class RiskGuard:
    def __init__(self, investment_cap=250):
        self.investment_cap = investment_cap
        self.ist = pytz.timezone("Asia/Kolkata")
        logging.info("RiskGuard initialized. Cap: $%s. Cutoff: 13:00 IST", investment_cap)

    def can_trade(self, current_exposure):
        now_ist = datetime.datetime.now(self.ist)
        
        # Hard cutoff at 1:00 PM IST (13:00)
        if now_ist.hour >= 13:
            logging.warning("Past 13:00 IST. Trading blocked.")
            return False
            
        if current_exposure >= self.investment_cap:
            logging.warning("Exposure %s exceeds cap %s", current_exposure, self.investment_cap)
            return False
            
        return True

    def should_force_exit(self):
        now_ist = datetime.datetime.now(self.ist)
        # If it is 13:00 IST or later, return True to trigger a mass sell-off
        if now_ist.hour >= 13:
            logging.info("FORCE EXIT: 13:00 IST reached. Closing all positions.")
            return True
        return False
