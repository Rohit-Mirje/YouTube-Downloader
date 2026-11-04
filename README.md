# ⚡ AuraStream - YouTube Video & Audio Downloader

A full-stack, cross-platform media downloader suite supporting **Desktop GUI (Windows)** and **Web App (Hostable on GitHub Pages)**.

---

## 🏗️ Project Architecture

```
YouTube Downloader/
├── docs/                       # 🌐 GitHub Pages Frontend (Static Web App)
│   ├── index.html              # Modern glassmorphic Web UI
│   ├── style.css               # Responsive dark theme
│   └── app.js                  # Connects to backend API, fetches info & downloads
│
├── server/                     # ⚙️ Backend API Server (yt-dlp + FFmpeg)
│   ├── server.py               # Flask REST API with CORS enabled
│   ├── requirements.txt        # Python backend dependencies
│   ├── Dockerfile              # Docker container for Render / Hugging Face Spaces
│   └── run_server.bat          # 1-click local backend runner for Windows
│
├── .github/workflows/          # 🚀 Automated GitHub Actions
│   └── deploy.yml              # Automatic deployment of docs/ to GitHub Pages
│
├── youtube_downloader.py       # 🖥️ Desktop GUI Application (CustomTkinter)
├── run_downloader.bat          # 1-click Desktop launcher
├── requirements.txt            # Desktop dependencies
└── README.md                   # Complete Guide & Documentation
```

---

## 🌐 Part 1: Hosting on GitHub Pages

GitHub Pages is a static host. Because YouTube downloads require stream processing, signature deciphering, and FFmpeg muxing, this project uses a **hybrid architecture**:
1. **Frontend (hosted on GitHub Pages)**: Serves the static web app.
2. **Backend (hosted on free cloud or local PC)**: Handles the `yt-dlp` stream extraction and FFmpeg processing.

### Step 1: Push Project to GitHub
1. Create a new repository on [GitHub](https://github.com/new) (e.g. `youtube-downloader`).
2. In your terminal inside `YouTube Downloader`:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of AuraStream YouTube Downloader"
   git branch -M main
   git remote add origin https://github.com/<YOUR_USERNAME>/youtube-downloader.git
   git push -u origin main
   ```

### Step 2: Enable GitHub Pages
1. Go to your GitHub repository -> **Settings** -> **Pages**.
2. Under **Build and deployment**:
   * **Source**: Choose **Deploy from a branch**.
   * **Branch**: Select `main` and choose folder **`/docs`**.
   * Click **Save**.
3. In ~30 seconds, your website will be live at:
   `https://<YOUR_USERNAME>.github.io/youtube-downloader/`

---

## ☁️ Part 2: Deploying the Backend API (Free Options)

Your GitHub Pages web app needs an API endpoint to process downloads. You have three easy options:

### Option A: Free Cloud Hosting on Render (Recommended)
1. Sign up for free at [render.com](https://render.com).
2. Click **New +** -> **Web Service**.
3. Connect your GitHub repository.
4. Set the following settings:
   * **Root Directory**: `server`
   * **Runtime**: `Python 3` (or `Docker`)
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `gunicorn --bind 0.0.0.0:$PORT server:app`
5. Click **Create Web Service**.
6. Copy your Render URL (e.g. `https://your-service.onrender.com`).
7. Open your GitHub Pages site, click the **Backend Settings** badge in the top right, paste your URL, and click **Save & Connect**!

### Option B: Free Cloud Hosting on Hugging Face Spaces
1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) -> **Create new Space**.
2. Select **Space SDK: Docker** (Blank).
3. Upload the files inside the `server/` folder (`Dockerfile`, `server.py`, `requirements.txt`).
4. Hugging Face will automatically build and run the container with pre-installed FFmpeg for free!

### Option C: Run Backend Locally on your PC
If you want to use the web app privately or across devices on your local Wi-Fi:
1. Double-click `server/run_server.bat` (starts at `http://localhost:5000`).
2. Open your GitHub Pages web app in your browser.
3. The app connects to `http://localhost:5000` automatically.

---

## 🖥️ Part 3: Desktop GUI App (Windows)

If you just want a native desktop application on Windows:
* Double-click **`run_downloader.bat`**.
* The desktop application opens instantly without needing a web browser or server.

---

## ✨ Features Included

* **🎯 Single Video Guarantee**: Automatically strips playlist/mix parameters (`&list=`, `&index=`, `&start_radio=`), preventing accidental mass downloads.
* **⚡ Instant Live Preview**: Fetches thumbnail, title, channel name, views, and duration automatically on link paste.
* **🎥 High Definition Video**: MP4 format up to 4K / 1080p Full HD with stream muxing.
* **🎵 High Bitrate Audio Extraction**: MP3 (320kbps, 256kbps, 192kbps, 128kbps) or original stream M4A with ID3 tags and embedded album art.
* **🔒 Cross-Origin (CORS) Enabled**: Ready to communicate across any domain or GitHub Pages URL.
