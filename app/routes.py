from flask import Blueprint, render_template, request, jsonify, send_from_directory, redirect, make_response, current_app
import os
from .config import Config
from .services.queue import job_queue
from .services.downloader import download_task

main_bp = Blueprint('main', __name__)

def _(key):
    from .translations import TRANSLATIONS
    lang = request.cookies.get('lang') or request.accept_languages.best_match(TRANSLATIONS.keys()) or 'en'
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/set_language/<lang>')
def set_language(lang):
    response = make_response(redirect('/'))
    response.set_cookie('lang', lang, max_age=30*24*60*60) # 30 days
    return response

@main_bp.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': _('error_no_url')}), 400
    
    # Add to queue
    job_id = job_queue.add_job(download_task, url, include_job_id=True)
    
    return jsonify({
        'message': _('download_queued'),
        'job_id': job_id
    })

@main_bp.route('/job/<job_id>')
def job_status(job_id):
    status = job_queue.get_job_status(job_id)
    if status is None:
        return jsonify({'error': 'not_found'}), 404
    return jsonify(status)

@main_bp.route('/status')
def status():
    return jsonify(job_queue.get_status())

@main_bp.route('/files')
def list_files():
    files = []
    # Ensure dir exists
    if not os.path.exists(Config.STAGING_DIR):
        try:
            os.makedirs(Config.STAGING_DIR)
        except OSError:
            pass # Might exist
        
    for root, dirs, filenames in os.walk(Config.STAGING_DIR):
        for filename in filenames:
            full_path = os.path.join(root, filename)
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
    return send_from_directory(os.path.abspath(Config.STAGING_DIR), filename, as_attachment=True)
