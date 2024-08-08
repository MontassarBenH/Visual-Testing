# config.py
import os
from configparser import ConfigParser

def load_config():
    config_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'config.ini')
    config = ConfigParser()
    config.read(config_path)
    return config

CONFIG = load_config()