from pathlib import Path
import sys

def get_base_path() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).resolve().parent.parent

BASE_PATH = get_base_path()
RESOURCES_PATH = BASE_PATH / "resources"