import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging() -> None:
    """
    Configures the application's logging system.
    Logs are written to the console and to a rotating file in the user's AppData directory.
    """
    app_name = "MediaMatrix"
    
    # Determine the log directory path
    if sys.platform == "win32":
        base_dir = os.getenv("APPDATA")
        if not base_dir:
            base_dir = os.path.expanduser("~")
    else:
        base_dir = os.path.expanduser("~/.config")
        
    log_dir = Path(base_dir) / app_name / "logs"
    
    # Create the directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "app.log"
    
    # Create formatters
    file_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - [%(threadName)s] %(module)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Set up Rotating File Handler (Max 5 MB, keep 3 backups)
    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Set up Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers if any to avoid duplication
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Capture standard Python warnings (like "Corrupt JPEG data")
    logging.captureWarnings(True)
    
    # Specifically route warnings logger to our handlers
    warnings_logger = logging.getLogger("py.warnings")
    warnings_logger.handlers = []
    warnings_logger.addHandler(file_handler)
    warnings_logger.addHandler(console_handler)
    warnings_logger.propagate = False
