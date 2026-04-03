import json
from pathlib import Path




BASE_DIR = Path(__file__).resolve().parent
print(BASE_DIR)

PROJECT_ROOT = BASE_DIR.parent.parent

domains_path = PROJECT_ROOT / "domains.json"

with open(domains_path, "r", encoding="utf-8") as f:
    domains_data = json.load(f)

