import os
import requests
import shutil
import yt_dlp
from urllib.parse import quote_plus
from ..config import Config, JobStage
from .integrations import run_beets_import
from .queue import job_queue
import logging
from datetime import datetime

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
        api_url = f"{Config.ODESLI_API_URL}{quote_plus(url)}"
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

def download_task(url, job_id=None):
    """
    Main task function to be executed by the worker.
    Resolves URL -> Downloads -> Imports -> Rescans.
    """
    def set_status(stage, state=None, message=None, error=None):
        if job_id:
            job_queue.update_job_status(job_id, stage=stage, state=state, message=message, error=error)

    set_status(stage=JobStage.RESOLVING_URL, state='processing', message='Resolving URL')

    resolved_url = resolve_url(url)
    logger.info(f"Starting download for: {resolved_url}")
    
    # Extract title from URL for display
    title = None
    try:
        # Try to extract from Odesli response or YouTube metadata
        if 'youtu' in resolved_url:
            # Will be updated with actual title from yt-dlp
            title = resolved_url.split('v=')[-1][:11]  # Video ID fallback
    except (ValueError, IndexError):
        title = None

    staging_root = Config.STAGING_DIR
    staging_dir = os.path.join(staging_root, job_id) if job_id else staging_root
    if job_id is None:
        # Use human-readable timestamp instead of UUID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        staging_dir = os.path.join(staging_root, timestamp)

    os.makedirs(staging_dir, exist_ok=True)

    # yt-dlp options
    audio_quality = Config.AUDIO_QUALITY
    if audio_quality.lower() == 'best':
        audio_quality = '0' # Best VBR quality

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': Config.AUDIO_CODEC,
            'preferredquality': audio_quality,
        }, {
            'key': 'FFmpegMetadata',
        }, {
            'key': 'EmbedThumbnail',
        }],
        'outtmpl': f'{staging_dir}/%(album|Unknown Album)s/%(playlist_index|00)s - %(title)s - %(artist|Unknown Artist)s.%(ext)s',
        'noplaylist': False,
        'ignoreerrors': True,
        'quiet': Config.YTDL_QUIET,
        'no_warnings': Config.YTDL_NO_WARNINGS,
        'keepvideo': False,
        'socket_timeout': 30,  # 30 second timeout
    }
    
    # Execute download
    try:
        set_status(stage=JobStage.DOWNLOADING, message='Downloading')
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(resolved_url, download=True)

            if not info:
                logger.error("Download failed: No info extracted.")
                set_status(stage=JobStage.FAILED, state='failed', error='No info extracted')
                return

            # Extract title from info and update status
            title = info.get('title', 'Unknown')
            artist = info.get('artist', info.get('uploader', 'Unknown Artist'))
            set_status(stage=JobStage.DOWNLOADING, message=f'Downloaded: {artist} - {title}')
        set_status(stage=JobStage.POSTPROCESSING, message='Post-processing')

        # Integrations
        import_success = False
        if Config.USE_BEETS:
            set_status(stage=JobStage.BEETS_IMPORT, message='Running beets import')
            # Import from staging to library
            import_success = run_beets_import(staging_dir)

        # Fallback to manual move if Beets disabled or failed
        if not Config.USE_BEETS or not import_success:
            if Config.USE_BEETS and not import_success:
                logger.warning("Beets import failed, falling back to manual move.")

            # Manual move from staging to download dir
            logger.info(f"Moving files from {staging_dir} to {Config.DOWNLOAD_DIR}")
            set_status(stage=JobStage.MOVING_FILES, message='Moving files to library')
            # Simplified move: merge directories
            if not os.path.exists(Config.DOWNLOAD_DIR):
                os.makedirs(Config.DOWNLOAD_DIR)

            try:
                # Iterate and move
                for root, dirs, files in os.walk(staging_dir):
                    for file in files:
                        src_path = os.path.join(root, file)
                        rel_path = os.path.relpath(src_path, staging_dir)
                        dest_path = os.path.join(Config.DOWNLOAD_DIR, rel_path)

                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        shutil.move(src_path, dest_path)

                # Cleanup staging for this job
                if os.path.exists(staging_dir):
                    shutil.rmtree(staging_dir)
            except Exception as e:
                logger.error(f"Error moving files: {e}")
                set_status(stage=JobStage.FAILED, state='failed', error=str(e))
                return
        else:
            # Beets already handled cleanup
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)

        set_status(stage=JobStage.DONE, state='completed', message='Download completed')
    except Exception as e:
        logger.error(f"Download task failed: {e}")
        set_status(stage=JobStage.FAILED, state='failed', error=str(e))
        raise e
