import re
from pathlib import Path

def process_file(path):
    s = path.read_text()
    orig = s
    if "datetime.now(timezone.utc)" in s:
        s = s.replace("datetime.now(timezone.utc)", "datetime.now(timezone.utc)")
        if "from datetime import datetime" in s and "from datetime import datetime, timezone" not in s:
            s = s.replace("from datetime import datetime", "from datetime import datetime, timezone")
    if "datetime.datetime.now(datetime.timezone.utc)" in s:
        s = s.replace("datetime.datetime.now(datetime.timezone.utc)", "datetime.datetime.now(datetime.timezone.utc)")
        if "import datetime" not in s:
            s = "import datetime\n" + s
    if s != orig:
        path.write_text(s)
        print("fixed", path)
for p in Path(".").rglob("*.py"):
    process_file(p)
