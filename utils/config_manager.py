# utils/config_manager.py
import os
import yaml

def load_config():
    """
    Load configuration from YAML file.
    Uses environment-specific config if available.
    
    Returns:
    --------
    dict
        Configuration dictionary
    """
    # Get environment
    env = os.environ.get('ENVIRONMENT', 'development')
    
    # Try to load environment-specific config
    config_path = f"config/config.{env}.yaml"
    
    # If environment-specific config doesn't exist, use default
    if not os.path.exists(config_path):
        config_path = "config/config.yaml"
        
    # Load and return config
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)