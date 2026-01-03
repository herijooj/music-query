from flask import Blueprint, render_template, request, jsonify, send_from_directory, redirect, make_response, current_app
from urllib.parse import urlparse
import os
from .config import Config
from .services.queue import job_queue
from .services.downloader import download_task

main_bp = Blueprint('main', __name__)


def get_translation(key: str) -> str:
    """Get translation for a key, respecting user's locale."""
    from .translations import TRANSLATIONS
    lang = request.cookies.get('lang') or request.accept_languages.best_match(TRANSLATIONS.keys()) or 'en'
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)


def is_valid_url(url: str) -> bool:
    """Validate that the string is a properly formatted URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except (ValueError, AttributeError):
        return False

@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/health')
def health():
    """
    Health check endpoint for uptime monitoring.
    ---
    tags:
      - System
    responses:
      200:
        description: Service is healthy
        schema:
          id: HealthResponse
          properties:
            status:
              type: string
              example: healthy
            timestamp:
              type: string
              format: date-time
              example: "2025-01-02T12:00:00Z"
    """
    from datetime import datetime, timezone
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

@main_bp.route('/set_language/<lang>')
def set_language(lang):
    from .translations import TRANSLATIONS
    if lang not in TRANSLATIONS:
        return redirect('/')
    response = make_response(redirect('/'))
    response.set_cookie(
        'lang', lang,
        max_age=30*24*60*60,
        secure=True,
        httponly=True,
        samesite='Lax'
    )
    return response

@main_bp.route('/download', methods=['POST'])
def download():
    """
    Queue a music download from URL (Spotify, YouTube, etc.)
    ---
    tags:
      - Downloads
    parameters:
      - in: formData
        name: url
        type: string
        required: true
        description: Music URL to download
    responses:
      200:
        description: Download queued successfully
        schema:
          id: DownloadQueued
          properties:
            message:
              type: string
              example: "Download queued"
            job_id:
              type: string
              format: uuid
              example: "550e8400-e29b-41d4-a716-446655440000"
      400:
        description: No URL provided
    """
    url = request.form.get('url')
    if not url:
        return jsonify({'error': get_translation('error_no_url')}), 400

    if not is_valid_url(url):
        return jsonify({'error': get_translation('error_invalid_url')}), 400

    # Add to queue
    job_id = job_queue.add_job(download_task, url, include_job_id=True)

    return jsonify({
        'message': get_translation('download_queued'),
        'job_id': job_id
    })

@main_bp.route('/job/<job_id>')
def job_status(job_id):
    """
    Get the status of a download job.
    ---
    tags:
      - Downloads
    parameters:
      - in: path
        name: job_id
        type: string
        format: uuid
        required: true
        description: Job ID returned from /download
    responses:
      200:
        description: Job status
        schema:
          id: JobStatus
          properties:
            stage:
              type: string
              example: "downloading"
            state:
              type: string
              example: "processing"
            message:
              type: string
              example: "Downloading"
      404:
        description: Job not found
    """
    status = job_queue.get_job_status(job_id)
    if status is None:
        return jsonify({'error': get_translation('error_not_found')}), 404
    return jsonify(status)

@main_bp.route('/status')
def status():
    """
    Get overall queue status.
    ---
    tags:
      - System
    responses:
      200:
        description: Queue status
        schema:
          id: QueueStatus
          properties:
            queue_size:
              type: integer
              example: 2
            current_job:
              type: object
    """
    return jsonify(job_queue.get_status())

@main_bp.route('/files')
def list_files():
    files = []
    # Ensure dir exists
    os.makedirs(Config.STAGING_DIR, exist_ok=True)

    for root, dirs, filenames in os.walk(Config.STAGING_DIR):
        for filename in filenames:
            rel_dir = os.path.relpath(root, Config.STAGING_DIR)
            if rel_dir == '.':
                rel_path = filename
            else:
                rel_path = os.path.join(rel_dir, filename)
            
            # Create display name: show album/filename, skip the timestamp folder
            parts = rel_path.split(os.sep)
            if len(parts) > 2:
                # Format: album/filename (skip timestamp)
                display_name = os.path.join(parts[1], parts[2])
            elif len(parts) == 2:
                # Format: album/filename (if already in this format)
                display_name = os.path.join(parts[0], parts[1])
            else:
                # Just filename
                display_name = filename
            
            files.append({
                'display': display_name,
                'path': rel_path
            })
    
    # Sort by display name
    files.sort(key=lambda x: x['display'])
    return jsonify(files)

@main_bp.route('/download_file/<path:filename>')
def download_file(filename):
    staging_abs = os.path.abspath(Config.STAGING_DIR)
    requested_path = os.path.abspath(os.path.join(staging_abs, filename))

    # Prevent path traversal: ensure requested path is within staging dir
    if not requested_path.startswith(staging_abs + os.sep) and requested_path != staging_abs:
        return jsonify({'error': 'Invalid path'}), 403

    return send_from_directory(staging_abs, filename, as_attachment=True)
