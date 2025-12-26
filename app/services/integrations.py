import subprocess
import os
import logging
import shutil
from ..config import Config

logger = logging.getLogger(__name__)

def run_beets_import(path):
    """
    Runs 'beet import -q' on the given path.
    Imports source 'path' (STAGING_DIR) into the library configured in beets.
    """
    if not Config.USE_BEETS:
        return True

    logger.info(f"Running Beets import from: {path}")
    try:
        cmd = ['beet'] + Config.BEETS_ARGS + [path]
        env = os.environ.copy()
        
        subprocess.run(cmd, check=True, env=env)
        
        # Clean up staging directory after import
        if os.path.exists(path):
            shutil.rmtree(path)
             
        logger.info("Beets import completed.")
        return True
    except Exception as e:
        logger.error(f"Beets import failed: {e}")
        return False
