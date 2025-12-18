import os
import requests
import yt_dlp
from ..config import Config
from .integrations import run_beets_import, trigger_rescans
import logging

logger = logging.getLogger(__name__)

def resolve_url(url):
    """
    Resolves a music URL to a YouTube/YouTube Music URL using Odesli.
    """
    # If it's already a youtube/youtu.be link, return it
    if 'youtube.com' in url or 'youtu.be' in url or 'music.youtube.com' in url:
        return url
    
    logger.info(f"Resolving URL: {url}")
    # Use Odesli to resolve
    try:
        api_url = f"{Config.ODESLI_API_URL}{url}"
        response = requests.get(api_url, timeout=Config.REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            links = data.get('linksByPlatform', {})
            # Prefer YouTube Music, then YouTube
            if 'youtubeMusic' in links:
                return links['youtubeMusic']['url']
            if 'youtube' in links:
                return links['youtube']['url']
    except Exception as e:
        logger.error(f"Error resolving URL: {e}")
    
    return url # Fallback to original URL

def download_task(url):
    """
    Main task function to be executed by the worker.
    Resolves URL -> Downloads -> Imports -> Rescans.
    """
    resolved_url = resolve_url(url)
    logger.info(f"Starting download for: {resolved_url}")
    
    if not os.path.exists(Config.DOWNLOAD_DIR):
        os.makedirs(Config.DOWNLOAD_DIR)

    # yt-dlp options
    audio_quality = Config.AUDIO_QUALITY
    if audio_quality.lower() == 'best':
        audio_quality = '0' # Best VBR quality

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': Config.AUDIO_CODEC,
            'preferredquality': audio_quality,
        }, {
            'key': 'FFmpegMetadata',
        }, {
            'key': 'EmbedThumbnail',
        }],
        'outtmpl': f'{Config.DOWNLOAD_DIR}/%(artist|Unknown Artist)s/%(album|Unknown Album)s/%(playlist_index|00)s - %(title)s - %(artist|Unknown Artist)s.%(ext)s',
        'noplaylist': False,
        'ignoreerrors': True,
        'quiet': False,
        'no_warnings': True,
    }
    
    # Execute download
    downloaded_files = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # nice process priority is handled by the OS for the python process usually, 
            # but we can try to set it for the subprocesses if we wrapped them.
            # standard yt-dlp doesn't expose easy 'nice' for ffmpeg, 
            # but since we are running in a single worker thread, we are already limiting concurrency.
            # We could use os.nice(10) in the worker thread, but that affects the whole thread/process if not careful.
            # For now, relying on the single-thread queue is the biggest optimization.
            
            info = ydl.extract_info(resolved_url, download=True)
            
            if not info:
                logger.error("Download failed: No info extracted.")
                return

            if 'entries' in info:
                entries = info['entries']
            else:
                entries = [info]
                
            for entry in entries:
                # Reconstruct path roughly or rely on return?
                # available in 'requested_downloads' sometimes.
                pass

        logger.info("Download finished.")
        
        # Integrations
        # Beets: Import the whole download directory or specific?
        # Safe bet for now: Config.DOWNLOAD_DIR. Beets is smart enough to skip already imported if configured right,
        # but -f might force it. 'beet import' usually handles new files.
        # Ideally we'd pass the exact folder.
        run_beets_import(Config.DOWNLOAD_DIR)
        
        # Rescans
        trigger_rescans()
        
    except Exception as e:
        logger.error(f"Download task failed: {e}")
        raise e
