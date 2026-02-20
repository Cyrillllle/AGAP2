from pathlib import Path
import shutil
from core.paths import RESOURCES_PATH

APP_NAME = "my_app"

USER_DATA_DIR = Path.home() / f".{APP_NAME}"
USER_DATA_DIR.mkdir(exist_ok=True)

DB_PATH = USER_DATA_DIR / "data.db"
TOKEN_PATH = USER_DATA_DIR / "vault"
JOB_PATH = USER_DATA_DIR / 'metiers.xlsx'
SKILLS_PATH = USER_DATA_DIR / 'skills.json'

def init_storage():
    if not JOB_PATH.exists() :
        shutil.copy(RESOURCES_PATH / "metiers.xlsx", JOB_PATH)
        # shutil.copy(RESOURCES_PATH / "skills.json", SKILLS_PATH)
        