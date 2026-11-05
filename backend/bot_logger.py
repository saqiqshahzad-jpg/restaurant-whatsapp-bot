import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from typing import List, Optional

# Ensure Windows terminal supports UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Determine logs directory
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BACKEND_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOGS_DIR, "restaurant_bot.log")

# ANSI Color Codes for terminal
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"

class ColoredConsoleFormatter(logging.Formatter):
    """Custom formatter providing distinct visual color tags for every system event."""
    def format(self, record):
        msg = record.getMessage()
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")

        # Color based on log level or special tag in message
        if record.levelno >= logging.ERROR:
            color = RED
            prefix = f"{BOLD}{RED}[ERROR ❌]{RESET}"
        elif record.levelno == logging.WARNING:
            color = YELLOW
            prefix = f"{BOLD}{YELLOW}[WARN ⚠️]{RESET}"
        elif "[OK]" in msg or "[SUCCESS]" in msg:
            color = GREEN
            prefix = f"{BOLD}{GREEN}[OK ✅]{RESET}"
        elif "[SECURITY]" in msg:
            color = RED
            prefix = f"{BOLD}{RED}[SECURITY 🛡️]{RESET}"
        elif "[LLM]" in msg:
            color = MAGENTA
            prefix = f"{BOLD}{MAGENTA}[AI/LLM 🧠]{RESET}"
        elif "[DB]" in msg:
            color = BLUE
            prefix = f"{BOLD}{BLUE}[DATABASE 💾]{RESET}"
        elif "[WA]" in msg or "[WHATSAPP]" in msg:
            color = GREEN
            prefix = f"{BOLD}{GREEN}[WHATSAPP 📱]{RESET}"
        elif "[CRON]" in msg or "[PING]" in msg:
            color = CYAN
            prefix = f"{BOLD}{CYAN}[CRON/PING ⏱️]{RESET}"
        else:
            color = CYAN
            prefix = f"{BOLD}{CYAN}[INFO ℹ️]{RESET}"

        clean_msg = msg
        for tag in ["[OK]", "[SUCCESS]", "[SECURITY]", "[LLM]", "[DB]", "[WA]", "[WHATSAPP]", "[CRON]", "[PING]"]:
            clean_msg = clean_msg.replace(tag, "").strip()

        return f"{CYAN}{timestamp}{RESET} {prefix} {clean_msg}"

class FileFormatter(logging.Formatter):
    """Clean plain-text format for file output without ANSI escape codes."""
    def format(self, record):
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname
        msg = record.getMessage()
        return f"[{timestamp}] [{level:<7}] {msg}"

def setup_logger(name: str = "RESTAURANT_BOT") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    # 1. Rotating File Handler (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(FileFormatter())
    logger.addHandler(file_handler)

    # 2. Colored Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredConsoleFormatter())
    logger.addHandler(console_handler)

    return logger

# Primary system logger
bot_logger = setup_logger("RESTAURANT_BOT")

# Convenience helper functions for standardized logging
def log_ok(tag: str, msg: str):
    bot_logger.info(f"[OK] [{tag}] {msg}")

def log_error(tag: str, msg: str, exc: Optional[Exception] = None):
    if exc:
        bot_logger.error(f"[ERROR] [{tag}] {msg} - Exception: {exc}", exc_info=True)
    else:
        bot_logger.error(f"[ERROR] [{tag}] {msg}")

def log_warn(tag: str, msg: str):
    bot_logger.warning(f"[{tag}] {msg}")

def log_info(tag: str, msg: str):
    bot_logger.info(f"[{tag}] {msg}")

def log_llm(tag: str, msg: str):
    bot_logger.info(f"[LLM] [{tag}] {msg}")

def log_db(tag: str, msg: str):
    bot_logger.info(f"[DB] [{tag}] {msg}")

def log_wa(tag: str, msg: str):
    bot_logger.info(f"[WA] [{tag}] {msg}")

def log_security(tag: str, msg: str):
    bot_logger.warning(f"[SECURITY] [{tag}] {msg}")

def log_cron(tag: str, msg: str):
    bot_logger.info(f"[CRON] [{tag}] {msg}")

def get_recent_log_lines(max_lines: int = 150) -> List[str]:
    """Read the last N lines of the log file for monitoring endpoints."""
    if not os.path.exists(LOG_FILE_PATH):
        return ["Log file has not been created yet."]
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return [line.rstrip() for line in lines[-max_lines:]]
    except Exception as e:
        return [f"Failed to read log file: {e}"]
