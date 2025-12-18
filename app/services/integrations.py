import subprocess
import requests
import os
import logging
from ..config import Config

logger = logging.getLogger(__name__)

def run_beets_import(path):
    """
    Runs 'beet import -q' on the given path.
    """
    if not Config.USE_BEETS:
        return

    logger.info(f"Running Beets import on: {path}")
    try:
        # -q for quiet (non-interactive) import
        cmd = ['beet'] + Config.BEETS_ARGS.split() + [path]
        subprocess.run(cmd, check=True)
        logger.info("Beets import completed.")
    except Exception as e:
        logger.error(f"Beets import failed: {e}")

def rescan_jellyfin():
    """
    Triggers a library rescan in Jellyfin.
    """
    if not Config.JELLYFIN_URL or not Config.JELLYFIN_API_KEY:
        return

    logger.info("Triggering Jellyfin rescan...")
    try:
        url = f"{Config.JELLYFIN_URL}/Library/Refresh"
        headers = {'X-Emby-Token': Config.JELLYFIN_API_KEY}
        response = requests.post(url, headers=headers, timeout=Config.REQUEST_TIMEOUT)
        
        if response.status_code == 204:
            logger.info("Jellyfin rescan triggered successfully.")
        else:
            logger.error(f"Jellyfin rescan failed: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error triggering Jellyfin rescan: {e}")

def rescan_navidrome():
    """
    Triggers a scan in Navidrome.
    """
    if not Config.NAVIDROME_URL or not Config.NAVIDROME_USER or not Config.NAVIDROME_TOKEN:
        return

    logger.info("Triggering Navidrome rescan...")
    try:
        # Navidrome Subsonic API or direct scan endpoint?
        # The typical Navidrome UI scan trigger often uses internal APIs.
        # But commonly we can use the Subsonic API 'startScan' if available,
        # or more reliably for Navidrome specific: /api/scan (if exposed) or similar.
        # Assuming standard Navidrome simplified approach often requested.
        
        # NOTE: Navidrome doesn't have a simple public API for scan without proper auth.
        # Users often use a script that touches the DB or calls the UI endpoint with headers.
        # For this implementation, we'll try a generic implementation assuming standard auth.
        
        url = f"{Config.NAVIDROME_URL}/api/scanner" # This is a guess/placeholder for the internal API often used
        # A more standard Subsonic way:
        # url = f"{Config.NAVIDROME_URL}/rest/startScan?u={Config.NAVIDROME_USER}&t={Config.NAVIDROME_TOKEN}&s={salt}&v=1.16.1&c=myapp"
        
        # Given the requirements, we'll try a generic approach or log if not perfectly standard.
        # Let's assume the user uses the Subsonic API method if they provided user/token.
        
        import hashlib
        import secrets
        salt = secrets.token_hex(6)
        token = hashlib.md5((Config.NAVIDROME_TOKEN + salt).encode('utf-8')).hexdigest()
        
        url = f"{Config.NAVIDROME_URL}/rest/startScan"
        params = {
            'u': Config.NAVIDROME_USER,
            't': token,
            's': salt,
            'v': '1.16.1',     # Subsonic API version
            'c': 'MusicQuery', # Client name
            'f': 'json'
        }
        
        response = requests.get(url, params=params, timeout=Config.REQUEST_TIMEOUT)
        data = response.json()
        
        if data.get('subsonic-response', {}).get('status') == 'ok':
             logger.info("Navidrome rescan triggered successfully.")
        else:
             logger.error(f"Navidrome rescan failed: {data}")

    except Exception as e:
        logger.error(f"Error triggering Navidrome rescan: {e}")

def trigger_rescans():
    rescan_jellyfin()
    rescan_navidrome()
