from flask import Blueprint, render_template, request, jsonify, send_from_directory
import os
from .config import Config
from .services.queue import job_queue
from .services.downloader import download_task

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    # Add to queue
    job_id = job_queue.add_job(download_task, url)
    
    return jsonify({
        'message': 'Download queued',
        'job_id': job_id
    })

@main_bp.route('/status')
def status():
    return jsonify(job_queue.get_status())

@main_bp.route('/files')
def list_files():
    files = []
    # Ensure dir exists
    if not os.path.exists(Config.DOWNLOAD_DIR):
        os.makedirs(Config.DOWNLOAD_DIR)
        
    for root, dirs, filenames in os.walk(Config.DOWNLOAD_DIR):
        for filename in filenames:
            rel_dir = os.path.relpath(root, Config.DOWNLOAD_DIR)
            if rel_dir == '.':
                files.append(filename)
            else:
                files.append(os.path.join(rel_dir, filename))
    files.sort()
    return jsonify(files)

@main_bp.route('/download_file/<path:filename>')
def download_file(filename):
    return send_from_directory(os.path.abspath(Config.DOWNLOAD_DIR), filename, as_attachment=True)
