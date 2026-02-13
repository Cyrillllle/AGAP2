from pathlib import Path
import shutil
from core.paths import RESOURCES_PATH

APP_NAME = "my_app"

USER_DATA_DIR = Path.home() / f".{APP_NAME}"
USER_DATA_DIR.mkdir(exist_ok=True)

DB_PATH = USER_DATA_DIR / "data.db"
TOKEN_PATH = USER_DATA_DIR / "vault"
JOB_PATH = USER_DATA_DIR / 'métiers Agap2 IT.xlsx'

def init_storage():
    """
    Étape 2 :
    - crée le dossier utilisateur
    - copie la DB initiale si absente
    """
    if not DB_PATH.exists() :
        shutil.copy(RESOURCES_PATH / "initial.db", DB_PATH)

    if not JOB_PATH.exists() :
        shutil.copy(RESOURCES_PATH / "métiers Agap2 IT.xlsx", JOB_PATH)
        