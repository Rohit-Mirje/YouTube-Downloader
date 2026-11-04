"""
YouTube Downloader Web API Server
Built with Flask, yt-dlp, and FFmpeg
"""

import os
import sys
import time
import shutil
import tempfile
import threading
from urllib.parse import urlparse, parse_qs
from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
# Enable CORS for all routes (allows GitHub Pages to call this API)
CORS(app, resources={r"/*": {"origins": "*"}})


def format_duration(seconds):
    if not seconds:
        return "Unknown"
    try:
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
    except Exception:
        return "Unknown"


def format_views(views):
    if views is None:
        return "N/A"
    try:
        views = int(views)
        if views >= 1_000_000_000:
            return f"{views / 1_000_000_000:.1f}B views"
        elif views >= 1_000_000:
            return f"{views / 1_000_000:.1f}M views"
        elif views >= 1_000:
            return f"{views / 1_000:.1f}K views"
        return f"{views} views"
    except Exception:
        return "N/A"


def sanitize_youtube_url(url, single_video=True):
    """
    Cleans a YouTube URL to extract just the single video ID,
    stripping playlist / mix parameters like &list=, &index=, &start_radio=, etc.
    """
    url = url.strip()
    if not url or not single_video:
        return url

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # youtu.be/VIDEO_ID
        if 'youtu.be' in domain:
            video_id = parsed.path.strip('/').split('?')[0].split('&')[0]
            if video_id:
                return f'https://www.youtube.com/watch?v={video_id}'

        # youtube.com/watch?v=VIDEO_ID
        if 'youtube.com' in domain and '/watch' in parsed.path:
            qs = parse_qs(parsed.query)
            if 'v' in qs and qs['v']:
                video_id = qs['v'][0]
                return f'https://www.youtube.com/watch?v={video_id}'

        # youtube.com/shorts/VIDEO_ID
        if 'youtube.com' in domain and '/shorts/' in parsed.path:
            video_id = parsed.path.split('/shorts/')[1].split('/')[0].split('?')[0]
            if video_id:
                return f'https://www.youtube.com/watch?v={video_id}'

        # youtube.com/live/VIDEO_ID
        if 'youtube.com' in domain and '/live/' in parsed.path:
            video_id = parsed.path.split('/live/')[1].split('/')[0].split('?')[0]
            if video_id:
                return f'https://www.youtube.com/watch?v={video_id}'

    except Exception:
        pass

    return url


def remove_temp_directory(directory_path, delay_seconds=20):
    """Safely deletes a temporary directory after a delay to ensure stream is finished."""
    def _remover():
        time.sleep(delay_seconds)
        try:
            if os.path.exists(directory_path):
                shutil.rmtree(directory_path, ignore_errors=True)
        except Exception:
            pass
    threading.Thread(target=_remover, daemon=True).start()


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "status": "online",
        "service": "YouTube Media Downloader API",
        "endpoints": {
            "health": "/health",
            "info": "POST /api/info",
            "download": "GET /api/download?url=...&mode=...&quality=..."
        }
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": time.time()})


@app.route('/api/info', methods=['POST', 'GET'])
def get_video_info():
    """Extracts metadata and preview information for a given YouTube URL."""
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        raw_url = data.get('url', '').strip()
        single_video = data.get('single_video', True)
    else:
        raw_url = request.args.get('url', '').strip()
        single_video = request.args.get('single_video', 'true').lower() == 'true'

    if not raw_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    target_url = sanitize_youtube_url(raw_url, single_video=single_video)

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': single_video,
        'nocheckcertificate': True,
        'js_runtimes': {'node': {}},
        'remote_components': {'ejs:github'},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if not info:
                return jsonify({"error": "Failed to fetch video information from YouTube."}), 404

            if 'entries' in info:
                entries = list(info['entries'])
                info = entries[0] if entries else info

            response_data = {
                "id": info.get('id'),
                "title": info.get('title', 'Unknown Title'),
                "uploader": info.get('uploader') or info.get('channel') or 'Unknown Channel',
                "duration": info.get('duration', 0),
                "duration_formatted": format_duration(info.get('duration')),
                "view_count": info.get('view_count'),
                "view_count_formatted": format_views(info.get('view_count')),
                "thumbnail": info.get('thumbnail'),
                "cleaned_url": target_url
            }
            return jsonify(response_data)

    except Exception as e:
        err_msg = str(e)
        if "Unsupported URL" in err_msg:
            clean_err = "Invalid or unsupported YouTube URL."
        elif "Private video" in err_msg:
            clean_err = "This video is private."
        elif "Sign in" in err_msg:
            clean_err = "Video requires sign-in or is age-restricted."
        else:
            clean_err = f"Extraction error: {err_msg[:120]}"
        return jsonify({"error": clean_err}), 400


@app.route('/api/download', methods=['GET', 'POST'])
def download_video():
    """Downloads requested video/audio and streams it directly to the browser."""
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        raw_url = data.get('url', '').strip()
        mode = data.get('mode', 'video').lower()
        quality = data.get('quality', 'best')
        single_video = data.get('single_video', True)
        embed_meta = data.get('embed_meta', True)
    else:
        raw_url = request.args.get('url', '').strip()
        mode = request.args.get('mode', 'video').lower()
        quality = request.args.get('quality', 'best')
        single_video = request.args.get('single_video', 'true').lower() == 'true'
        embed_meta = request.args.get('embed_meta', 'true').lower() == 'true'

    if not raw_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    target_url = sanitize_youtube_url(raw_url, single_video=single_video)

    # Create temporary directory for download
    temp_dir = tempfile.mkdtemp(prefix="ytdl_")
    outtmpl = os.path.join(temp_dir, '%(title)s.%(ext)s')

    ydl_opts = {
        'outtmpl': outtmpl,
        'noplaylist': single_video,
        'nocheckcertificate': True,
        'windowsfilenames': True,
        'quiet': True,
        'no_warnings': True,
        'js_runtimes': {'node': {}},
        'remote_components': {'ejs:github'},
    }

    is_audio = 'audio' in mode

    if not is_audio:
        # Video formats
        if quality in ['1080', '1080p']:
            ydl_opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]'
        elif quality in ['720', '720p']:
            ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]'
        elif quality in ['480', '480p']:
            ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]'
        elif quality in ['360', '360p']:
            ydl_opts['format'] = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]'
        else:
            # Best available
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best'

        ydl_opts['merge_output_format'] = 'mp4'

    else:
        # Audio formats
        if quality.lower() == 'm4a':
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
        else:
            bitrate = '320'
            if '256' in quality:
                bitrate = '256'
            elif '192' in quality:
                bitrate = '192'
            elif '128' in quality:
                bitrate = '128'

            ydl_opts['format'] = 'bestaudio/best'
            postprocessors = [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': bitrate,
                }
            ]
            if embed_meta:
                postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})
                postprocessors.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})
                ydl_opts['writethumbnail'] = True

            ydl_opts['postprocessors'] = postprocessors

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=True)
            if not info:
                remove_temp_directory(temp_dir, delay_seconds=1)
                return jsonify({"error": "Download failed, no stream found."}), 400

            if 'entries' in info:
                entries = list(info['entries'])
                info = entries[0] if entries else info

            # Locate downloaded file
            final_file = None
            if 'requested_downloads' in info and len(info['requested_downloads']) > 0:
                final_file = info['requested_downloads'][0].get('filepath')

            if not final_file or not os.path.exists(final_file):
                prep = ydl.prepare_filename(info)
                base, _ = os.path.splitext(prep)
                ext = ".mp3" if is_audio and quality.lower() != 'm4a' else ".mp4"
                candidate = base + ext
                if os.path.exists(candidate):
                    final_file = candidate
                elif os.path.exists(prep):
                    final_file = prep

            if not final_file or not os.path.exists(final_file):
                # Search temp directory for any media file
                files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if not f.endswith('.temp') and not f.endswith('.part')]
                if files:
                    final_file = files[0]
                else:
                    remove_temp_directory(temp_dir, delay_seconds=1)
                    return jsonify({"error": "Processed file was not found."}), 500

            filename = os.path.basename(final_file)
            remove_temp_directory(temp_dir, delay_seconds=60)

            return send_file(
                final_file,
                as_attachment=True,
                download_name=filename
            )

    except Exception as e:
        remove_temp_directory(temp_dir, delay_seconds=1)
        return jsonify({"error": f"Download failed: {str(e)[:150]}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting YouTube Downloader Server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
