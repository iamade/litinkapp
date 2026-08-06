import os
import re

from app.core.config import settings
from loguru import logger

logger.remove()

IDENTITY_LIKE_PATTERN = re.compile(r"\b[A-Z2-7]{58}\b")


def redact_identity_like_output(message: object) -> str:
    """Redact startup identity values such as Algorand account addresses."""
    return IDENTITY_LIKE_PATTERN.sub("[REDACTED_IDENTITY]", str(message))


def _redact_log_record(record):
    record["message"] = redact_identity_like_output(record["message"])


logger.configure(patcher=_redact_log_record)

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
# LOG_DIR =os.path.join(os.path.dirname(__file__), "logs")

LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} - "
    "{message}"
) 

logger.add(
    sink=os.path.join(LOG_DIR,"debug.log"),
    format=LOG_FORMAT,
    level="DEBUG" if settings.ENVIRONMENT == "local" else "INFO",
    filter= lambda record: record["level"].no <= logger.level("WARNING").no,
    rotation="10MB",
    retention="30 days",
    compression="zip" 
)

logger.add(
    sink=os.path.join(LOG_DIR,"error.log"),
    format=LOG_FORMAT,
    level="ERROR",
    rotation="10MB",
    retention="30 days",
    compression="zip",
    backtrace=True,
    diagnose=True
)

def get_logger():
    return logger
