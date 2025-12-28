import json
import time
from pathlib import Path

from bean import Device
token_path = Path('.cache/token')

def curr_milliseconds() -> int:
    return int(time.time() * 1000)


def ensure_dir_exists(path: Path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

def save_active_code(activ_code: str):
    ensure_dir_exists(token_path)
    token_file = token_path / 'token'
    token_file.write_text(activ_code)


def load_active_code():
    token_file = token_path / 'token'
    if not token_file.exists():
        return None
    token_file = token_path / 'token'
    return token_file.read_text()
