import os
import shlex
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Configuration
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change-in-prod')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

    # App Settings
    DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', 'downloads') # Final Destination
    STAGING_DIR = os.getenv('STAGING_DIR', 'staging')     # Temp folder
    
    # Integrations
    USE_BEETS = os.getenv('USE_BEETS', 'False').lower() == 'true'
    
    # Performance / Hardware
    # Limits for low-end hardware
    MAX_CONCURRENT_DOWNLOADS = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', 1))
    PROCESS_NICE_VALUE = int(os.getenv('PROCESS_NICE_VALUE', 10)) # Lower priority for heavy tasks
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 10))

    # External APIs
    ODESLI_API_URL = os.getenv('ODESLI_API_URL', 'https://api.song.link/v1-alpha.1/links?url=')

    # Tool Arguments
    BEETS_ARGS = shlex.split(os.getenv('BEETS_ARGS', 'import -q'))

    # Audio Download Settings
    AUDIO_CODEC = os.getenv('AUDIO_CODEC', 'm4a')
    AUDIO_QUALITY = os.getenv('AUDIO_QUALITY', '192')
