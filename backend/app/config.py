import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'procurement.db'}")
REDIS_URL = os.getenv("REDIS_URL", "")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-env")
JWT_HOURS = int(os.getenv("JWT_HOURS", "12"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "claude-sonnet-5-5")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@company.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_NAME = os.getenv("ADMIN_NAME", "مشرف النظام")

# مستويات الموافقة حسب قيمة الطلب (ريال)
LEVEL_FINANCE_FROM = float(os.getenv("LEVEL_FINANCE_FROM", "5000"))
LEVEL_GM_FROM = float(os.getenv("LEVEL_GM_FROM", "50000"))
SINGLE_QUOTE_LIMIT = LEVEL_FINANCE_FROM
