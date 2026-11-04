# ⚡ YouTube Video & Audio Downloader

A modern desktop application built with **CustomTkinter**, **yt-dlp**, and **FFmpeg** for downloading high-quality videos and extracting pristine audio from YouTube.

---

## 🚀 Quick Start

### 1. One-Click Launcher (Windows)
Double-click `run_downloader.bat`.
- Automatically validates dependencies
- Launches cleanly in the background without keeping a terminal open

### 2. Manual Terminal Launch
```bash
python youtube_downloader.py
```

---

## ✨ Features & Capabilities

- **🎯 Single Video Guarantee**:
  - Automatically cleans YouTube URLs, stripping playlist/mix identifiers (`&list=`, `&index=`, `&start_radio=`).
  - Sets `'noplaylist': True` to ensure that only the requested video is fetched and downloaded, never an entire series or playlist by accident.
  - Includes a **"Single video only"** checkbox if you ever want to toggle playlist downloading intentionally.

- **⚡ Instant Auto-Fetch & Preview**:
  - Auto-fetches video metadata, title, channel, duration, view count, and high-res thumbnail as soon as you paste or type a link.
  - Fast extraction (~2–3 seconds) with real-time status indication.

- **🎥 High-Definition Video**:
  - Best Available (Up to 4K / 1080p MP4)
  - 1080p Full HD
  - 720p HD
  - 480p / 360p Data Saver
  - Automatically merges high-resolution video streams with audio via FFmpeg.

- **🎵 Audio Extraction**:
  - MP3 320 kbps (Extreme Quality)
  - MP3 256 kbps (High Quality)
  - MP3 192 kbps (Standard Quality)
  - MP3 128 kbps (Compact)
  - M4A (Original High-Res Audio)
  - **Embedded Metadata & Cover Art**: Automatically injects YouTube thumbnail as album artwork and tags artist/title into the MP3 file.

- **📂 Folder & Music Player Integration**:
  - Defaults to your `Downloads` folder.
  - **"Set to Music Player Folder"** button to download songs directly into your **Music Player** directory.
  - Direct "Play / Open File" and "Show in Explorer" buttons upon download completion.
