import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _normalize_database_url(raw: str) -> str:
    if raw.startswith("postgres://"):
        return raw.replace("postgres://", "postgresql+psycopg://", 1)
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    DATABASE_URL = _normalize_database_url(DATABASE_URL)
    DATA_DIR = None
    DB_PATH = None
    DB_LABEL = "PostgreSQL"
else:
    DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH = DATA_DIR / os.getenv("DB_NAME", "lottery_mvp.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    DB_LABEL = f"SQLite ({DB_PATH.name})"

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DEFAULT_FREE_DAILY_AI_LIMIT = int(os.getenv("FREE_DAILY_AI_LIMIT", "1"))
DEFAULT_PAID_DAILY_AI_LIMIT = int(os.getenv("PAID_DAILY_AI_LIMIT", "5"))
DEFAULT_ACCESS_CODE_DAYS = int(os.getenv("DEFAULT_ACCESS_CODE_DAYS", "30"))
ALLOW_DEMO_FALLBACK = os.getenv("ALLOW_DEMO_FALLBACK", "1") == "1"
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "20"))
SOURCE_USER_AGENT = os.getenv(
    "SOURCE_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
)

LOTTERY_CONFIG = {
    "ssq": {
        "name": "双色球",
        "main_count": 6,
        "main_min": 1,
        "main_max": 33,
        "extra_count": 1,
        "extra_min": 1,
        "extra_max": 16,
    },
    "dlt": {
        "name": "大乐透",
        "main_count": 5,
        "main_min": 1,
        "main_max": 35,
        "extra_count": 2,
        "extra_min": 1,
        "extra_max": 12,
    },
    "fc3d": {
        "name": "福彩3D",
        "main_count": 3,
        "main_min": 0,
        "main_max": 9,
        "extra_count": 0,
        "extra_min": 0,
        "extra_max": 0,
    },
    "pl3": {
        "name": "排列3",
        "main_count": 3,
        "main_min": 0,
        "main_max": 9,
        "extra_count": 0,
        "extra_min": 0,
        "extra_max": 0,
    },
    "pl5": {
        "name": "排列5",
        "main_count": 5,
        "main_min": 0,
        "main_max": 9,
        "extra_count": 0,
        "extra_min": 0,
        "extra_max": 0,
    },
    "qlc": {
        "name": "七乐彩",
        "main_count": 7,
        "main_min": 1,
        "main_max": 30,
        "extra_count": 1,
        "extra_min": 1,
        "extra_max": 30,
    },
    "kl8": {
        "name": "快乐8",
        "main_count": 20,
        "main_min": 1,
        "main_max": 80,
        "extra_count": 0,
        "extra_min": 0,
        "extra_max": 0,
    },
}

LOTTERY_OPTIONS = {cfg["name"]: key for key, cfg in LOTTERY_CONFIG.items()}

OFFICIAL_SOURCE_URLS = {
    "ssq": os.getenv("SOURCE_URL_SSQ", "https://www.cwl.gov.cn/ygkj/ssq/kjgg/"),
    "dlt": os.getenv("SOURCE_URL_DLT", "https://m.lottery.gov.cn/tcwm/dlt/"),
    "fc3d": os.getenv("SOURCE_URL_FC3D", "https://www.cwl.gov.cn/ygkj/3d/kjgg/"),
    "pl3": os.getenv("SOURCE_URL_PL3", "https://m.lottery.gov.cn/tcwm/pls/"),
    "pl5": os.getenv("SOURCE_URL_PL5", "https://m.lottery.gov.cn/tcwm/plw/"),
    "qlc": os.getenv("SOURCE_URL_QLC", "https://www.cwl.gov.cn/ygkj/qlc/kjgg/"),
    "kl8": os.getenv("SOURCE_URL_KL8", "https://www.cwl.gov.cn/ygkj/kl8/kjgg/"),
}
