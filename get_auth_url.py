import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from execution.schwab_client import SchwabClient

print('\n👉 COPY THIS URL TO YOUR BROWSER:\n', SchwabClient().get_auth_url())
