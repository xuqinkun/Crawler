import time
from pathlib import Path

def curr_milliseconds() -> int:
    return int(time.time() * 1000)


def ensure_dir_exists(path: Path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)