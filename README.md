# Music Query

A simple web interface for searching music, downloading from YouTube (via `yt-dlp`), and organizing with `beets`.

## Features

- **Multi-platform support**: Paste links from Spotify, Apple Music, Deezer, etc.
- **Odesli Integration**: Resolves links to canonical YouTube/YouTube Music IDs.
- **Automated Tagging**: Embeds Title, Artist, Album, and Cover Art (Thumbnail) into the MP3/M4A.
- **Beets Integration**: Optionally use your existing `beets` setup for advanced library management and tagging.
 

## Prerequisites

- Python 3.x
- `ffmpeg` (Required for audio extraction and tagging)

```bash
sudo apt update && sudo apt install ffmpeg -y
```

## Installation

1. Clone this repository or copy the files.
1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Configure the application by editing the `.env` file.

## Running the App

```bash
python run.py
```

With a process manager (e.g., gunicorn):

```bash
gunicorn wsgi:app --bind 0.0.0.0:5000
```

The app will be available at `http://localhost:5000`.

## Beets Integration

If you have `beets` installed and configured on your server, you can enable it by setting `USE_BEETS=True` in the `.env` file. When enabled, the app will run `beet import -q` on every downloaded file, allowing your existing beets configuration (plugins, library paths, etc.) to handle the file.

## Configuration notes

- `SECRET_KEY` is used for session signing.
- `LOG_LEVEL` sets the verbosity (DEBUG, INFO, WARNING, ERROR).
