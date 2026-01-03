# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Music Query is a Flask web application for searching and downloading music from YouTube (via yt-dlp), with support for multi-platform links (Spotify, Apple Music, Deezer) through Odesli API integration and optional beets library management.

## Commands

```bash
# Run development server
python run.py

# Run with gunicorn (production)
gunicorn wsgi:app --bind 0.0.0.0:5000

# Install dependencies
pip install -r requirements.txt
```

**Prerequisites**: ffmpeg must be installed for audio extraction and tagging (`sudo apt install ffmpeg`).

## Architecture

```
run.py          → Entry point, creates app via factory
wsgi.py         → WSGI wrapper for production servers
app/
  __init__.py   → App factory, logging, i18n context processor
  config.py     → Configuration via python-dotenv
  routes.py     → Flask Blueprint with HTTP endpoints
  translations.py → i18n dictionary (en, pt, pt-br)
  services/
    queue.py        → JobQueue singleton (threading-based background worker)
    downloader.py   → yt-dlp download logic, Odesli URL resolution
    integrations.py → Beets subprocess integration
  static/       → CSS/JS assets
  templates/    → HTML templates (index.html)
```

### Key Patterns

- **JobQueue**: Singleton pattern managing background download workers via `threading.Thread`
- **URL Resolution**: Non-YouTube links are resolved via Odesli API to get YouTube/YouTube Music IDs
- **i18n**: Translations injected into templates via `context_processor`; language detected from cookie or `Accept-Language` header

## Configuration

All settings are environment-based (see `.env` and `config.py`):

| Variable | Description |
|----------|-------------|
| `USE_BEETS` | Enable beets import instead of manual file move |
| `MAX_CONCURRENT_DOWNLOADS` | Number of parallel download workers |
| `AUDIO_CODEC` | Output format (m4a, mp3) |
| `AUDIO_QUALITY` | Bitrate quality |
| `DOWNLOAD_DIR` | Final destination for files |
| `STAGING_DIR` | Temporary download staging area |
