from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.parking_service import inspect_parking_data


def main() -> None:
    print(json.dumps(inspect_parking_data(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
