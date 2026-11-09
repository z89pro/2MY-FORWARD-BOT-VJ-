"""
config.py — Advanced Unified Configuration for Forward Bot
Supports both Ultra-Forward-Bot Config class and module-level constants.
Reads priority:
  1. System environment variables  (Koyeb / Render / Railway / Docker)
  2. .env file                     (Local development)
  3. Hardcoded defaults            (Fallback)
"""
import os
try:
    from dotenv import load_dotenv
    # Load .env with override so local .env takes precedence
    load_dotenv(override=True)
except ImportError:
    pass

_DEFAULTS = {
    "API_ID":             "34439627",
    "API_HASH":           "e5c7efb57949e742889aa96bf64c4552",
    "BOT_TOKEN":          "8432833653:AAHrsIx0gasQwv7eAJv6DHbyYTjcPRNziyY",
    "BOT_SESSION":        "Auto_Forward",
    "DATABASE_URI":       "mongodb+srv://rajaualkhan33729_db_user:hlYTpjnHZzGDljKX@cluster0.vylyp51.mongodb.net/?appName=Cluster0",
    "DATABASE_NAME":      "UltraForwardBot",
    "BOT_OWNER_ID":       "8349955493 7115200195",
    "LOG_CHANNEL":        "0",
    "DUMP_CHANNEL":       "0",
    "FORCE_SUB_CHANNEL":  "",
    "FORCE_SUB_ON":       "False",
    "PORT":               "8080",
    "REFERRAL_ENABLED":   "True",
    "REFERRAL_POINTS_PER_JOIN": "10",
    "REFERRAL_WELCOME_BONUS": "5",
    "VERIFY_ENABLED":     "True",
    "VERIFY_DURATION":    "24",
    "VERIFY_STEPS":       "1",
    "VERIFY_MODE":        "step",
    "SHORTENER_URL":      "shareus.io",
    "SHORTENER_API":      "",
    "SHORTENER_URL2":     "",
    "SHORTENER_API2":     "",
    "SHORTENER_URL3":     "",
    "SHORTENER_API3":     "",
    "TOKEN_TIMEOUT":      "30",
    "VERIFY_TUTORIAL":    "",
    "UPI_ID":             "",
    "UPI_NAME":           "Skinet Premium",
    "ADMIN_CONTACT":      "@TheSkinet",
    "CRYPTO_ADDRESS":     "",
}

def _get(key: str, alt_keys: tuple = ()) -> str:
    """Reads from system env -> alternative env keys -> _DEFAULTS fallback."""
    val = os.environ.get(key)
    if val:
        return val.strip()
    for alt in alt_keys:
        alt_val = os.environ.get(alt)
        if alt_val:
            return alt_val.strip()
    return str(_DEFAULTS.get(key, "")).strip()


class Config:
    API_ID = int(_get("API_ID")) if _get("API_ID").isdigit() else 0
    API_HASH = _get("API_HASH")
    BOT_TOKEN = _get("BOT_TOKEN")
    BOT_SESSION = _get("BOT_SESSION") or "Auto_Forward"
    DATABASE_URI = _get("DATABASE_URI", ("MONGO_URI", "DATABASE"))
    DATABASE_NAME = _get("DATABASE_NAME") or "UltraForwardBot"

    # Multi-admin support: handles space/comma-separated IDs cleanly
    _raw_owners = _get("BOT_OWNER_ID", ("OWNER_ID",)).replace(",", " ")
    BOT_OWNER_ID = [
        int(x) for x in _raw_owners.split()
        if x.lstrip("-").isdigit()
    ]

    _raw_log = _get("LOG_CHANNEL", ("LOG_CHANNEL_ID",))
    if _raw_log in ("-1003584084546", "0", ""):
        LOG_CHANNEL = 0
    elif _raw_log.lstrip("-").isdigit():
        LOG_CHANNEL = int(_raw_log)
    else:
        LOG_CHANNEL = 0

    _raw_dump = _get("DUMP_CHANNEL", ("DUMP_CHANNEL_ID",))
    DUMP_CHANNEL = int(_raw_dump) if _raw_dump.lstrip("-").isdigit() else 0

    FORCE_SUB_CHANNEL = _get("FORCE_SUB_CHANNEL")
    FORCE_SUB_ON = _get("FORCE_SUB_ON").lower() in ("true", "1", "yes")
    PORT = int(_get("PORT")) if _get("PORT").isdigit() else 8080

    REFERRAL_ENABLED = _get("REFERRAL_ENABLED").lower() in ("true", "1", "yes")
    REFERRAL_POINTS_PER_JOIN = int(_get("REFERRAL_POINTS_PER_JOIN")) if _get("REFERRAL_POINTS_PER_JOIN").isdigit() else 10
    REFERRAL_WELCOME_BONUS = int(_get("REFERRAL_WELCOME_BONUS")) if _get("REFERRAL_WELCOME_BONUS").isdigit() else 5

    VERIFY_ENABLED = _get("VERIFY_ENABLED").lower() in ("true", "1", "yes")
    VERIFY_DURATION = int(_get("VERIFY_DURATION")) if _get("VERIFY_DURATION").isdigit() else 24
    VERIFY_STEPS = int(_get("VERIFY_STEPS")) if _get("VERIFY_STEPS").isdigit() else 1
    VERIFY_MODE = _get("VERIFY_MODE") or "step"
    SHORTENER_URL = _get("SHORTENER_URL") or "shareus.io"
    SHORTENER_API = _get("SHORTENER_API")
    SHORTENER_URL2 = _get("SHORTENER_URL2")
    SHORTENER_API2 = _get("SHORTENER_API2")
    SHORTENER_URL3 = _get("SHORTENER_URL3")
    SHORTENER_API3 = _get("SHORTENER_API3")
    TOKEN_TIMEOUT = int(_get("TOKEN_TIMEOUT")) if _get("TOKEN_TIMEOUT").isdigit() else 30
    VERIFY_TUTORIAL = _get("VERIFY_TUTORIAL")
    UPI_ID = _get("UPI_ID")
    UPI_NAME = _get("UPI_NAME") or "Skinet Premium"
    ADMIN_CONTACT = _get("ADMIN_CONTACT") or "@TheSkinet"
    CRYPTO_ADDRESS = _get("CRYPTO_ADDRESS")


class temp(object):
    lock = {}
    CANCEL = {}
    PAUSE = {}
    LIVE_TASKS = {}
    forwardings = 0
    BANNED_USERS = []
    IS_FRWD_CHAT = []


# ── Module-level Aliases for Full Backward Compatibility ────────
API_ID         = Config.API_ID
API_HASH       = Config.API_HASH
BOT_TOKEN      = Config.BOT_TOKEN
BOT_SESSION    = Config.BOT_SESSION
DATABASE_URI   = Config.DATABASE_URI
MONGO_URI      = Config.DATABASE_URI
DATABASE_NAME  = Config.DATABASE_NAME
BOT_OWNER_ID   = Config.BOT_OWNER_ID
OWNER_ID       = Config.BOT_OWNER_ID[0] if Config.BOT_OWNER_ID else 0
LOG_CHANNEL    = Config.LOG_CHANNEL
LOG_CHANNEL_ID = Config.LOG_CHANNEL
DUMP_CHANNEL   = Config.DUMP_CHANNEL
FORCE_SUB_CHANNEL = Config.FORCE_SUB_CHANNEL
FORCE_SUB_ON   = Config.FORCE_SUB_ON
PORT           = Config.PORT
VERIFY_ENABLED = Config.VERIFY_ENABLED
VERIFY_DURATION = Config.VERIFY_DURATION
VERIFY_STEPS   = Config.VERIFY_STEPS
SHORTENER_URL  = Config.SHORTENER_URL
SHORTENER_API  = Config.SHORTENER_API

# ── Forward Engine Default Presets ─────────────────────────────
FAST_BATCH_SIZE    = 100
FAST_BATCH_COUNT   = 10
FAST_DELAY         = 1.0
FAST_BREAK_SECONDS = 300

SAFE_BATCH_SIZE    = 20
SAFE_BATCH_COUNT   = 10
SAFE_DELAY         = 5.0
SAFE_BREAK_SECONDS = 60
