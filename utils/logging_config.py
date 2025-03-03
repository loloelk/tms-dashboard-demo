# utils/logging_config.py
import logging
import os
from datetime import datetime

def configure_logging():
    """
    Configure logging for the application.
    Creates a log directory if it doesn't exist and sets up logging.
    """
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Create a log file with current date
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f'app_{today}.log')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Log application startup
    logging.info("Application started")