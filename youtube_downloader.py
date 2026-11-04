"""
YouTube Video and Audio Downloader Desktop Application
Built with CustomTkinter, yt-dlp, and FFmpeg
"""

import os
import sys
import io
import re
import threading
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image
import requests
import yt_dlp


# Set CustomTkinter theme and appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


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


def format_bytes(bytes_num):
    if not bytes_num:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"


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


def contains_playlist_param(url):
    """Checks whether the URL contains playlist or mix parameters."""
    if not url:
        return False
    u = url.lower()
    return ('list=' in u or '/playlist' in u or 'start_radio=' in u)


class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("YouTube Media Downloader")
        self.geometry("860x780")
        self.minsize(780, 700)

        # State variables
        self.current_video_info = None
        self.current_thumbnail_img = None
        self.is_downloading = False
        self.is_fetching = False
        self.cancel_requested = False
        self.last_downloaded_file = None
        self.default_download_dir = str(Path.home() / "Downloads")
        music_player_candidate = Path(__file__).resolve().parent.parent / "Music Player"
        if music_player_candidate.exists():
            self.music_player_dir = str(music_player_candidate)
        else:
            self.music_player_dir = str(Path(__file__).resolve().parent)

        self._debounce_timer = None
        self._last_fetched_url = ""

        # UI Setup
        self._setup_ui()

    def _setup_ui(self):
        # Main container with scrolling support
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=15)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # 1. Header Section
        self._create_header()

        # 2. URL Input Section
        self._create_url_section()

        # 3. Video Preview Card
        self._create_preview_section()

        # 4. Format & Destination Options
        self._create_options_section()

        # 5. Download Progress & Controls
        self._create_progress_section()

    def _create_header(self):
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text="⚡ YouTube Downloader",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Download single HD/4K videos or extract pristine MP3 songs",
            font=ctk.CTkFont(size=13),
            text_color="gray70"
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Appearance mode switch
        self.theme_switch = ctk.CTkSwitch(
            header_frame,
            text="Dark Mode",
            command=self._toggle_appearance,
            onvalue="Dark",
            offvalue="Light"
        )
        self.theme_switch.select()
        self.theme_switch.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

    def _create_url_section(self):
        url_card = ctk.CTkFrame(self.main_frame, corner_radius=12)
        url_card.grid(row=1, column=0, sticky="ew", pady=(0, 15), padx=2)
        url_card.grid_columnconfigure(0, weight=1)

        card_title = ctk.CTkLabel(
            url_card,
            text="Video Link",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        card_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(12, 6))

        # Input row
        input_frame = ctk.CTkFrame(url_card, fg_color="transparent")
        input_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 8))
        input_frame.grid_columnconfigure(0, weight=1)

        self.url_var = tk.StringVar()
        self.url_var.trace_add("write", self._on_url_input_changed)

        self.url_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.url_var,
            placeholder_text="Paste YouTube URL here (e.g. https://www.youtube.com/watch?v=...)",
            height=40,
            font=ctk.CTkFont(size=13)
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self.fetch_info())
        self.url_entry.bind("<Control-v>", lambda e: self.after(50, self.fetch_info))
        self.url_entry.bind("<<Paste>>", lambda e: self.after(50, self.fetch_info))

        self.paste_btn = ctk.CTkButton(
            input_frame,
            text="📋 Paste",
            width=80,
            height=40,
            command=self._paste_clipboard
        )
        self.paste_btn.grid(row=0, column=1, padx=(0, 8))

        self.fetch_btn = ctk.CTkButton(
            input_frame,
            text="🔍 Fetch Info",
            width=100,
            height=40,
            fg_color="#1f538d",
            hover_color="#14375e",
            command=self.fetch_info
        )
        self.fetch_btn.grid(row=0, column=2)

        # Options row directly under URL entry
        sub_row = ctk.CTkFrame(url_card, fg_color="transparent")
        sub_row.grid(row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))
        sub_row.grid_columnconfigure(1, weight=1)

        self.single_video_var = ctk.BooleanVar(value=True)
        self.single_video_cb = ctk.CTkCheckBox(
            sub_row,
            text="Single video only (ignore playlist/mix if present in link)",
            variable=self.single_video_var,
            font=ctk.CTkFont(size=12),
            command=self._on_single_video_toggle
        )
        self.single_video_cb.grid(row=0, column=0, sticky="w")

        self.url_hint_label = ctk.CTkLabel(
            sub_row,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#E3A008",
            anchor="e"
        )
        self.url_hint_label.grid(row=0, column=1, sticky="e")

    def _create_preview_section(self):
        self.preview_card = ctk.CTkFrame(self.main_frame, corner_radius=12)
        self.preview_card.grid(row=2, column=0, sticky="ew", pady=(0, 15), padx=2)
        self.preview_card.grid_columnconfigure(1, weight=1)

        # Thumbnail display container
        self.thumb_label = ctk.CTkLabel(
            self.preview_card,
            text="📷\nPaste a link to preview",
            width=210,
            height=125,
            corner_radius=8,
            fg_color=("gray85", "gray20"),
            font=ctk.CTkFont(size=13)
        )
        self.thumb_label.grid(row=0, column=0, padx=16, pady=16, sticky="nw")

        # Info column
        self.info_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.info_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=16)
        self.info_frame.grid_columnconfigure(0, weight=1)

        self.video_title_label = ctk.CTkLabel(
            self.info_frame,
            text="No video loaded yet",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
            justify="left",
            wraplength=500
        )
        self.video_title_label.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.channel_label = ctk.CTkLabel(
            self.info_frame,
            text="Channel: --",
            font=ctk.CTkFont(size=13),
            text_color="gray70",
            anchor="w"
        )
        self.channel_label.grid(row=1, column=0, sticky="w", pady=2)

        self.stats_row = ctk.CTkLabel(
            self.info_frame,
            text="Duration: --  •  Views: --",
            font=ctk.CTkFont(size=13),
            text_color="gray70",
            anchor="w"
        )
        self.stats_row.grid(row=2, column=0, sticky="w", pady=2)

        self.status_tag = ctk.CTkLabel(
            self.info_frame,
            text="Status: Waiting for URL",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray60",
            anchor="w"
        )
        self.status_tag.grid(row=3, column=0, sticky="w", pady=(6, 0))

    def _create_options_section(self):
        options_card = ctk.CTkFrame(self.main_frame, corner_radius=12)
        options_card.grid(row=3, column=0, sticky="ew", pady=(0, 15), padx=2)
        options_card.grid_columnconfigure((0, 1), weight=1)

        # Column 1: Mode & Quality
        col1 = ctk.CTkFrame(options_card, fg_color="transparent")
        col1.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

        col1_title = ctk.CTkLabel(
            col1,
            text="Format & Quality Settings",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        col1_title.grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Format switch (Video / Audio)
        self.format_mode = ctk.CTkSegmentedButton(
            col1,
            values=["🎥 Video (MP4)", "🎵 Audio (MP3)"],
            command=self._on_format_mode_change
        )
        self.format_mode.set("🎥 Video (MP4)")
        self.format_mode.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        # Quality dropdown label & menu
        self.quality_label = ctk.CTkLabel(
            col1,
            text="Select Resolution:",
            font=ctk.CTkFont(size=13)
        )
        self.quality_label.grid(row=2, column=0, sticky="w", pady=(0, 4))

        self.video_qualities = [
            "Best Available (Up to 4K / 1080p)",
            "1080p (Full HD)",
            "720p (HD)",
            "480p (Standard)",
            "360p (Data Saver)"
        ]
        self.audio_qualities = [
            "MP3 - 320 kbps (Extreme Quality)",
            "MP3 - 256 kbps (High Quality)",
            "MP3 - 192 kbps (Standard Quality)",
            "MP3 - 128 kbps (Compact)",
            "M4A (Original Stream)"
        ]

        self.quality_dropdown = ctk.CTkOptionMenu(
            col1,
            values=self.video_qualities,
            height=34
        )
        self.quality_dropdown.set(self.video_qualities[0])
        self.quality_dropdown.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        # Checkbox for embedding metadata
        self.embed_meta_var = ctk.BooleanVar(value=True)
        self.embed_meta_cb = ctk.CTkCheckBox(
            col1,
            text="Embed Metadata & Thumbnail (Audio)",
            variable=self.embed_meta_var,
            font=ctk.CTkFont(size=12)
        )
        self.embed_meta_cb.grid(row=4, column=0, sticky="w")
        self.embed_meta_cb.configure(state="disabled")

        # Column 2: Destination Folder
        col2 = ctk.CTkFrame(options_card, fg_color="transparent")
        col2.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)

        col2_title = ctk.CTkLabel(
            col2,
            text="Save Destination",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        col2_title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.dest_entry = ctk.CTkEntry(
            col2,
            height=34,
            font=ctk.CTkFont(size=12)
        )
        self.dest_entry.insert(0, self.default_download_dir)
        self.dest_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Buttons row for destination
        btn_row = ctk.CTkFrame(col2, fg_color="transparent")
        btn_row.grid(row=2, column=0, columnspan=2, sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.browse_btn = ctk.CTkButton(
            btn_row,
            text="📁 Browse Folder",
            height=32,
            command=self._browse_folder
        )
        self.browse_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.open_dest_btn = ctk.CTkButton(
            btn_row,
            text="📂 Open Folder",
            height=32,
            fg_color="gray30",
            hover_color="gray40",
            command=self._open_destination_folder
        )
        self.open_dest_btn.grid(row=0, column=1, sticky="ew")

        # Quick preset button for Music Player folder
        self.use_music_folder_btn = ctk.CTkButton(
            col2,
            text="🎵 Set to Music Player Folder",
            height=28,
            fg_color="transparent",
            text_color=("gray20", "gray80"),
            border_width=1,
            border_color=("gray70", "gray40"),
            command=self._set_music_player_folder
        )
        self.use_music_folder_btn.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _create_progress_section(self):
        progress_card = ctk.CTkFrame(self.main_frame, corner_radius=12)
        progress_card.grid(row=4, column=0, sticky="ew", pady=(0, 15), padx=2)
        progress_card.grid_columnconfigure(0, weight=1)

        # Action Buttons Row
        action_row = ctk.CTkFrame(progress_card, fg_color="transparent")
        action_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        action_row.grid_columnconfigure(0, weight=3)
        action_row.grid_columnconfigure(1, weight=1)

        self.download_btn = ctk.CTkButton(
            action_row,
            text="⬇ Start Download",
            height=44,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2EA043",
            hover_color="#238636",
            command=self.start_download
        )
        self.download_btn.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            action_row,
            text="⏹ Cancel",
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#DA3633",
            hover_color="#B62324",
            state="disabled",
            command=self.cancel_download
        )
        self.cancel_btn.grid(row=0, column=1, sticky="ew")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(progress_card, height=14)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        # Status and Stats Labels
        stats_frame = ctk.CTkFrame(progress_card, fg_color="transparent")
        stats_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        stats_frame.grid_columnconfigure(0, weight=1)

        self.progress_status_label = ctk.CTkLabel(
            stats_frame,
            text="Ready to download.",
            font=ctk.CTkFont(size=13),
            anchor="w"
        )
        self.progress_status_label.grid(row=0, column=0, sticky="w")

        self.progress_speed_label = ctk.CTkLabel(
            stats_frame,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="gray70",
            anchor="e"
        )
        self.progress_speed_label.grid(row=0, column=1, sticky="e")

        # Completion Action Bar (Appears after download)
        self.completion_frame = ctk.CTkFrame(progress_card, fg_color="transparent")
        self.completion_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.completion_frame.grid_columnconfigure((0, 1), weight=1)
        self.completion_frame.grid_remove()

        self.open_file_btn = ctk.CTkButton(
            self.completion_frame,
            text="▶ Play / Open File",
            height=34,
            fg_color="#1f538d",
            hover_color="#14375e",
            command=self._open_downloaded_file
        )
        self.open_file_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.show_in_folder_btn = ctk.CTkButton(
            self.completion_frame,
            text="📂 Show in Explorer",
            height=34,
            fg_color="gray30",
            hover_color="gray40",
            command=self._highlight_file_in_explorer
        )
        self.show_in_folder_btn.grid(row=0, column=1, sticky="ew")

    # ---------------- UI Callbacks & Actions ----------------

    def _toggle_appearance(self):
        mode = self.theme_switch.get()
        ctk.set_appearance_mode(mode)

    def _on_url_input_changed(self, *args):
        raw_url = self.url_var.get().strip()

        # Update hint if playlist detected
        if contains_playlist_param(raw_url):
            if self.single_video_var.get():
                self.url_hint_label.configure(text="ℹ️ Playlist detected: Downloading single video only.")
            else:
                self.url_hint_label.configure(text="⚠️ Playlist mode ON: Will download entire playlist.")
        else:
            self.url_hint_label.configure(text="")

        # Auto-fetch debounce
        if self._debounce_timer:
            self.after_cancel(self._debounce_timer)
            self._debounce_timer = None

        if len(raw_url) >= 15 and ('youtube.com' in raw_url.lower() or 'youtu.be' in raw_url.lower()):
            if raw_url != self._last_fetched_url:
                self._debounce_timer = self.after(600, self.fetch_info)

    def _on_single_video_toggle(self):
        raw_url = self.url_var.get().strip()
        if contains_playlist_param(raw_url):
            if self.single_video_var.get():
                self.url_hint_label.configure(text="ℹ️ Playlist detected: Downloading single video only.")
            else:
                self.url_hint_label.configure(text="⚠️ Playlist mode ON: Will download entire playlist.")
        else:
            self.url_hint_label.configure(text="")

        # Re-fetch info when toggle changes
        if raw_url:
            self.fetch_info()

    def _paste_clipboard(self):
        try:
            text = self.clipboard_get().strip()
            if text:
                self.url_var.set(text)
                self.fetch_info()
        except Exception:
            pass

    def _on_format_mode_change(self, mode):
        if "Video" in mode:
            self.quality_label.configure(text="Select Video Resolution:")
            self.quality_dropdown.configure(values=self.video_qualities)
            self.quality_dropdown.set(self.video_qualities[0])
            self.embed_meta_cb.configure(state="disabled")
        else:
            self.quality_label.configure(text="Select Audio Bitrate:")
            self.quality_dropdown.configure(values=self.audio_qualities)
            self.quality_dropdown.set(self.audio_qualities[0])
            self.embed_meta_cb.configure(state="normal")

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.dest_entry.get())
        if folder:
            self.dest_entry.delete(0, tk.END)
            self.dest_entry.insert(0, os.path.normpath(folder))

    def _open_destination_folder(self):
        path = self.dest_entry.get().strip()
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning("Folder Not Found", f"The directory '{path}' does not exist.")

    def _set_music_player_folder(self):
        self.dest_entry.delete(0, tk.END)
        self.dest_entry.insert(0, self.music_player_dir)

    def _open_downloaded_file(self):
        if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
            try:
                os.startfile(self.last_downloaded_file)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {e}")

    def _highlight_file_in_explorer(self):
        if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
            subprocess.Popen(f'explorer /select,"{os.path.normpath(self.last_downloaded_file)}"')
        else:
            self._open_destination_folder()

    # ---------------- Fetch Video Metadata ----------------

    def fetch_info(self):
        raw_url = self.url_var.get().strip()
        if not raw_url:
            return

        if self.is_fetching or self.is_downloading:
            return

        is_single = self.single_video_var.get()
        target_url = sanitize_youtube_url(raw_url, single_video=is_single)
        self._last_fetched_url = raw_url

        self.is_fetching = True
        self.fetch_btn.configure(state="disabled")
        self.status_tag.configure(text="Status: Fetching details...", text_color="#E3A008")
        self.video_title_label.configure(text="Fetching video metadata, please wait...")
        self.thumb_label.configure(image="", text="⏳\nLoading...")

        threading.Thread(target=self._fetch_info_thread, args=(target_url, is_single), daemon=True).start()

    def _fetch_info_thread(self, target_url, is_single):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'noplaylist': is_single,
            'nocheckcertificate': True,
            'js_runtimes': {'node': {}},
            'remote_components': {'ejs:github'},
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                if not info:
                    raise Exception("No information returned by YouTube.")

                # If a playlist object was returned, pick the first video entry
                if 'entries' in info:
                    entries = list(info['entries'])
                    if entries:
                        info = entries[0]
                    else:
                        raise Exception("No videos found in this link.")

                self.current_video_info = info
                self.after(0, self._update_preview_ui, info)

        except Exception as e:
            err_msg = str(e)
            if "Unsupported URL" in err_msg:
                err_clean = "Invalid or unsupported YouTube URL."
            elif "Private video" in err_msg:
                err_clean = "This video is private."
            elif "Sign in" in err_msg:
                err_clean = "Video requires sign-in or is age-restricted."
            else:
                err_clean = f"Error: {err_msg[:120]}"

            self.after(0, self._on_fetch_error, err_clean)

    def _update_preview_ui(self, info):
        self.is_fetching = False
        self.fetch_btn.configure(state="normal")

        title = info.get('title', 'Unknown Title')
        channel = info.get('uploader') or info.get('channel') or 'Unknown Channel'
        duration = format_duration(info.get('duration'))
        views = format_views(info.get('view_count'))

        self.video_title_label.configure(text=title)
        self.channel_label.configure(text=f"Channel: {channel}")
        self.stats_row.configure(text=f"Duration: {duration}  •  Views: {views}")
        self.status_tag.configure(text="Status: Ready to Download", text_color="#2EA043")

        # Fetch and display thumbnail
        thumb_url = info.get('thumbnail')
        if thumb_url:
            threading.Thread(target=self._load_thumbnail_thread, args=(thumb_url,), daemon=True).start()
        else:
            self.thumb_label.configure(image="", text="📷\nNo Thumbnail")

    def _load_thumbnail_thread(self, thumb_url):
        try:
            resp = requests.get(thumb_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
            if resp.status_code == 200:
                self.after(0, self._set_thumbnail_image, resp.content)
            else:
                self.after(0, lambda: self.thumb_label.configure(image="", text="📷\nNo Thumbnail"))
        except Exception:
            self.after(0, lambda: self.thumb_label.configure(image="", text="📷\nNo Thumbnail"))

    def _set_thumbnail_image(self, img_bytes):
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            img = img.resize((210, 125), Image.Resampling.LANCZOS)
            self.current_thumbnail_img = ctk.CTkImage(light_image=img, dark_image=img, size=(210, 125))
            self.thumb_label.configure(image=self.current_thumbnail_img, text="")
        except Exception:
            self.thumb_label.configure(image="", text="📷\nPreview Error")

    def _on_fetch_error(self, message):
        self.is_fetching = False
        self.fetch_btn.configure(state="normal")
        self.status_tag.configure(text="Status: Fetch Failed", text_color="#DA3633")
        self.video_title_label.configure(text=message)
        self.thumb_label.configure(image="", text="❌\nError")

    # ---------------- Download Execution ----------------

    def start_download(self):
        raw_url = self.url_var.get().strip()
        if not raw_url:
            messagebox.showwarning("URL Required", "Please enter a YouTube video URL.")
            return

        save_dir = self.dest_entry.get().strip()
        if not save_dir:
            messagebox.showwarning("Folder Required", "Please select a download folder.")
            return

        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Folder Error", f"Cannot create directory: {e}")
                return

        is_single = self.single_video_var.get()
        target_url = sanitize_youtube_url(raw_url, single_video=is_single)

        mode = self.format_mode.get()
        quality_choice = self.quality_dropdown.get()
        embed_meta = self.embed_meta_var.get()

        # UI state during download
        self.is_downloading = True
        self.cancel_requested = False
        self.last_downloaded_file = None
        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.fetch_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_status_label.configure(text="Initializing download...")
        self.progress_speed_label.configure(text="")
        self.completion_frame.grid_remove()

        threading.Thread(
            target=self._download_worker,
            args=(target_url, save_dir, mode, quality_choice, embed_meta, is_single),
            daemon=True
        ).start()

    def cancel_download(self):
        if self.is_downloading:
            self.cancel_requested = True
            self.progress_status_label.configure(text="Cancelling download...")
            self.cancel_btn.configure(state="disabled")

    def _download_progress_hook(self, d):
        if self.cancel_requested:
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")

        status = d.get('status')
        if status == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            speed = d.get('speed')
            eta = d.get('eta')

            if total and total > 0:
                fraction = min(max(downloaded / total, 0.0), 1.0)
                percent = int(fraction * 100)
                pct_str = f"{percent}%"
            else:
                fraction = 0.5
                pct_str = ""

            down_str = format_bytes(downloaded)
            tot_str = format_bytes(total) if total else "--"
            speed_str = f"{format_bytes(speed)}/s" if speed else ""
            eta_str = f"ETA: {int(eta)}s" if eta is not None else ""

            status_text = f"Downloading: {pct_str} ({down_str} / {tot_str})"
            speed_text = f"{speed_str}  {eta_str}".strip()

            self.after(0, self._update_progress_ui, fraction, status_text, speed_text)

        elif status == 'finished':
            self.after(0, self._update_progress_ui, 1.0, "Processing with FFmpeg...", "")

    def _postprocessor_hook(self, d):
        if self.cancel_requested:
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")

        status = d.get('status')
        pp = d.get('postprocessor', '')
        if status == 'started':
            if 'ExtractAudio' in pp:
                self.after(0, self._update_progress_ui, 1.0, "Extracting & converting audio to MP3...", "")
            elif 'Merger' in pp:
                self.after(0, self._update_progress_ui, 1.0, "Merging video and audio streams...", "")
            elif 'Metadata' in pp:
                self.after(0, self._update_progress_ui, 1.0, "Embedding metadata & artwork...", "")

    def _update_progress_ui(self, fraction, status_text, speed_text):
        self.progress_bar.set(fraction)
        self.progress_status_label.configure(text=status_text)
        self.progress_speed_label.configure(text=speed_text)

    def _download_worker(self, target_url, save_dir, mode, quality_choice, embed_meta, is_single):
        outtmpl = os.path.join(save_dir, '%(title)s.%(ext)s')

        ydl_opts = {
            'outtmpl': outtmpl,
            'progress_hooks': [self._download_progress_hook],
            'postprocessor_hooks': [self._postprocessor_hook],
            'noplaylist': is_single,
            'nocheckcertificate': True,
            'windowsfilenames': True,
            'quiet': True,
            'no_warnings': True,
            'js_runtimes': {'node': {}},
            'remote_components': {'ejs:github'},
        }

        # Configure Video vs Audio formats
        if "Video" in mode:
            if "Best Available" in quality_choice:
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best'
            elif "1080p" in quality_choice:
                ydl_opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]'
            elif "720p" in quality_choice:
                ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]'
            elif "480p" in quality_choice:
                ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]'
            elif "360p" in quality_choice:
                ydl_opts['format'] = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]'
            else:
                ydl_opts['format'] = 'bestvideo+bestaudio/best'

            ydl_opts['merge_output_format'] = 'mp4'

        else:
            # Audio mode
            if "M4A" in quality_choice:
                ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
            else:
                # MP3 extraction
                bitrate = "320"
                if "256" in quality_choice:
                    bitrate = "256"
                elif "192" in quality_choice:
                    bitrate = "192"
                elif "128" in quality_choice:
                    bitrate = "128"

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
                    raise Exception("Download failed, no metadata received.")

                if 'entries' in info:
                    entries = list(info['entries'])
                    info = entries[0] if entries else info

                # Determine final downloaded filepath
                final_file = None
                if 'requested_downloads' in info and len(info['requested_downloads']) > 0:
                    final_file = info['requested_downloads'][0].get('filepath')

                if not final_file:
                    prep = ydl.prepare_filename(info)
                    base, _ = os.path.splitext(prep)
                    ext = ".mp3" if ("Audio" in mode and "MP3" in quality_choice) else ".mp4"
                    candidate = base + ext
                    if os.path.exists(candidate):
                        final_file = candidate
                    elif os.path.exists(prep):
                        final_file = prep

                self.last_downloaded_file = final_file
                self.after(0, self._on_download_success, final_file)

        except yt_dlp.utils.DownloadCancelled:
            self.after(0, self._on_download_cancelled)
        except Exception as e:
            self.after(0, self._on_download_error, str(e))

    def _on_download_success(self, filepath):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.fetch_btn.configure(state="normal")
        self.progress_bar.set(1.0)

        filename = os.path.basename(filepath) if filepath else "File"
        self.progress_status_label.configure(
            text=f"✅ Download complete! Saved: {filename[:45]}...",
            text_color="#2EA043"
        )
        self.progress_speed_label.configure(text="")
        self.completion_frame.grid()

        # Update preview card if empty
        if self.current_video_info:
            self._update_preview_ui(self.current_video_info)

        # Brief notification
        messagebox.showinfo("Success", f"Download finished successfully!\n\nSaved to:\n{filepath}")

    def _on_download_cancelled(self):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.fetch_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_status_label.configure(
            text="⚠️ Download cancelled by user.",
            text_color="#DA3633"
        )
        self.progress_speed_label.configure(text="")

    def _on_download_error(self, err_msg):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.fetch_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_status_label.configure(
            text="❌ Download failed.",
            text_color="#DA3633"
        )
        self.progress_speed_label.configure(text="")

        clean_err = err_msg
        if "HTTP Error 403" in err_msg:
            clean_err = "HTTP Error 403: Forbidden. YouTube blocked this stream request. Please update yt-dlp (`pip install -U yt-dlp`) and try again."
        elif "ffprobe/ffmpeg and avprobe/avconv not found" in err_msg:
            clean_err = "FFmpeg is required to merge or convert this format."

        messagebox.showerror("Download Error", f"Failed to download video:\n\n{clean_err[:300]}")


if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()
