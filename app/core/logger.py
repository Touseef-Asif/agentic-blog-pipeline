"""
logger.py — Loguru logging setup.

Import `logger` from this module everywhere in the project.
Reads LOG_LEVEL from environment (default: INFO).
"""

import os
import sys

from dotenv import load_dotenv
from loguru import logger

# Load .env so LOG_LEVEL is available before anything else
load_dotenv()

# Remove the default Loguru handler and add a clean one
logger.remove()
logger.add(
    sys.stderr,
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> — {message}",
    colorize=True,
)
