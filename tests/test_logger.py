import pytest
import os
import logging
from pathlib import Path
from unittest.mock import patch

# Add src to sys.path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.logger import setup_logging

def test_setup_logging_creates_directory():
    # Use a temporary directory for APPDATA mock
    with patch('os.getenv', return_value=str(Path('./temp_appdata'))):
        setup_logging()
        
        log_dir = Path('./temp_appdata/MediaMatrix/logs')
        assert log_dir.exists()
        assert (log_dir / "app.log").exists()
        
        # Cleanup
        # Note: We don't want to mess up real logging if it's already running, 
        # but in a test environment this should be fine.
        for handler in logging.root.handlers[:]:
            handler.close()
            logging.root.removeHandler(handler)
        
        # Remove temp files
        import shutil
        if Path('./temp_appdata').exists():
            shutil.rmtree('./temp_appdata')

def test_logger_levels():
    with patch('os.getenv', return_value=str(Path('./temp_appdata_2'))):
        setup_logging()
        logger = logging.getLogger("test_logger")
        
        # Should not crash
        logger.info("Test INFO message")
        logger.error("Test ERROR message")
        
        # Cleanup
        for handler in logging.root.handlers[:]:
            handler.close()
            logging.root.removeHandler(handler)
        
        import shutil
        if Path('./temp_appdata_2').exists():
            shutil.rmtree('./temp_appdata_2')
