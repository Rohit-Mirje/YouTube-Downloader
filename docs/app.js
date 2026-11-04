/**
 * AuraStream - YouTube Downloader Web App
 * Static Client for GitHub Pages + Cloud / Local Backend
 */

// Configuration & State
const DEFAULT_LOCAL_BACKEND = "http://localhost:5000";
let backendUrl = localStorage.getItem("ytdl_backend_url") || DEFAULT_LOCAL_BACKEND;
let currentMode = "video"; // 'video' or 'audio'
let currentVideoInfo = null;
let isDownloading = false;
let debounceTimeout = null;

// DOM Elements
const urlInput = document.getElementById("url-input");
const btnPaste = document.getElementById("btn-paste");
const btnFetch = document.getElementById("btn-fetch");
const singleVideoCb = document.getElementById("single-video-cb");
const urlHint = document.getElementById("url-hint");

const previewCard = document.getElementById("preview-card");
const videoThumbnail = document.getElementById("video-thumbnail");
const thumbPlaceholder = document.getElementById("thumb-placeholder");
const videoTitle = document.getElementById("video-title");
const videoChannel = document.getElementById("video-channel");
const videoDuration = document.getElementById("video-duration");
const videoViews = document.getElementById("video-views");
const statusTag = document.getElementById("status-tag");

const btnModeVideo = document.getElementById("btn-mode-video");
const btnModeAudio = document.getElementById("btn-mode-audio");
const qualityLabel = document.getElementById("quality-label");
const qualitySelect = document.getElementById("quality-select");

const btnDownload = document.getElementById("btn-download");
const btnDownloadText = document.getElementById("btn-download-text");
const progressContainer = document.getElementById("progress-container");
const progressBarFill = document.getElementById("progress-bar-fill");
const progressStatus = document.getElementById("progress-status");
const progressDetail = document.getElementById("progress-detail");
const resultBox = document.getElementById("result-box");
const resultFilename = document.getElementById("result-filename");

const backendPill = document.getElementById("btn-backend-settings");
const backendStatusDot = document.getElementById("backend-status-dot");
const backendStatusText = document.getElementById("backend-status-text");
const backendModal = document.getElementById("backend-modal");
const btnCloseModal = document.getElementById("btn-close-modal");
const backendUrlInput = document.getElementById("backend-url-input");
const btnTestBackend = document.getElementById("btn-test-backend");
const btnSaveBackend = document.getElementById("btn-save-backend");
const backendTestStatus = document.getElementById("backend-test-status");
const presetLocal = document.getElementById("preset-local");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  backendUrlInput.value = backendUrl;
  checkBackendHealth(backendUrl);
  setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
  // Mode selection
  btnModeVideo.addEventListener("click", () => setMode("video"));
  btnModeAudio.addEventListener("click", () => setMode("audio"));

  // Input & Fetch
  btnPaste.addEventListener("click", handlePaste);
  btnFetch.addEventListener("click", () => fetchMetadata());
  urlInput.addEventListener("input", handleUrlInput);
  urlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") fetchMetadata();
  });
  singleVideoCb.addEventListener("change", handleUrlInput);

  // Download
  btnDownload.addEventListener("click", handleDownload);

  // Backend Modal
  backendPill.addEventListener("click", openBackendModal);
  btnCloseModal.addEventListener("click", closeBackendModal);
  backendModal.addEventListener("click", (e) => {
    if (e.target === backendModal) closeBackendModal();
  });
  btnTestBackend.addEventListener("click", () => testBackendConnection(backendUrlInput.value.trim()));
  btnSaveBackend.addEventListener("click", saveBackendSettings);
  presetLocal.addEventListener("click", () => {
    backendUrlInput.value = DEFAULT_LOCAL_BACKEND;
  });
}

// ---------------- Backend Health & Settings ----------------

async function checkBackendHealth(url) {
  backendStatusDot.className = "status-dot disconnected";
  backendStatusText.textContent = "Backend: Connecting...";

  try {
    const cleanUrl = url.replace(/\/+$/, "");
    const res = await fetch(`${cleanUrl}/health`, { method: "GET", mode: "cors" });
    if (res.ok) {
      backendStatusDot.className = "status-dot connected";
      const displayHost = new URL(cleanUrl).host;
      backendStatusText.textContent = `Backend: ${displayHost}`;
      return true;
    }
  } catch (err) {
    // Backend offline or unreachable
  }

  backendStatusDot.className = "status-dot disconnected";
  backendStatusText.textContent = "Backend: Offline (Click to configure)";
  return false;
}

function openBackendModal() {
  backendUrlInput.value = backendUrl;
  backendTestStatus.textContent = "";
  backendModal.style.display = "flex";
}

function closeBackendModal() {
  backendModal.style.display = "none";
}

async function testBackendConnection(url) {
  if (!url) {
    backendTestStatus.innerHTML = '<span style="color: #ef4444;">Please enter a URL.</span>';
    return;
  }
  const cleanUrl = url.replace(/\/+$/, "");
  backendTestStatus.innerHTML = '<span style="color: #38bdf8;">Testing connection...</span>';

  try {
    const res = await fetch(`${cleanUrl}/health`, { method: "GET", mode: "cors" });
    if (res.ok) {
      backendTestStatus.innerHTML = '<span style="color: #22c55e;">✓ Successfully connected to backend API!</span>';
      return;
    }
  } catch (err) {
    // Error
  }

  backendTestStatus.innerHTML = '<span style="color: #ef4444;">✗ Unable to reach backend. Ensure your backend server is running and CORS is enabled.</span>';
}

function saveBackendSettings() {
  const newUrl = backendUrlInput.value.trim().replace(/\/+$/, "");
  if (!newUrl) return;

  backendUrl = newUrl;
  localStorage.setItem("ytdl_backend_url", backendUrl);
  checkBackendHealth(backendUrl);
  closeBackendModal();
}

// ---------------- Mode & Format Options ----------------

function setMode(mode) {
  currentMode = mode;
  if (mode === "video") {
    btnModeVideo.classList.add("active");
    btnModeAudio.classList.remove("active");
    qualityLabel.textContent = "Resolution";
    qualitySelect.innerHTML = `
      <option value="best">Best Available (Up to 4K / 1080p)</option>
      <option value="1080">1080p (Full HD)</option>
      <option value="720">720p (HD)</option>
      <option value="480">480p (Standard)</option>
      <option value="360">360p (Data Saver)</option>
    `;
  } else {
    btnModeAudio.classList.add("active");
    btnModeVideo.classList.remove("active");
    qualityLabel.textContent = "Audio Bitrate";
    qualitySelect.innerHTML = `
      <option value="320">MP3 - 320 kbps (Extreme Quality)</option>
      <option value="256">MP3 - 256 kbps (High Quality)</option>
      <option value="192">MP3 - 192 kbps (Standard Quality)</option>
      <option value="128">MP3 - 128 kbps (Compact)</option>
      <option value="m4a">M4A (Original Stream)</option>
    `;
  }
}

// ---------------- URL & Playlist Sanitization ----------------

function sanitizeYoutubeUrl(url, singleVideo = true) {
  url = url.trim();
  if (!url || !singleVideo) return url;

  try {
    const parsed = new URL(url);
    const domain = parsed.hostname.toLowerCase();

    // youtu.be/VIDEO_ID
    if (domain.includes("youtu.be")) {
      const videoId = parsed.pathname.replace(/^\//, "").split("?")[0].split("&")[0];
      if (videoId) return `https://www.youtube.com/watch?v=${videoId}`;
    }

    // youtube.com/watch?v=VIDEO_ID
    if (domain.includes("youtube.com") && parsed.pathname.includes("/watch")) {
      const v = parsed.searchParams.get("v");
      if (v) return `https://www.youtube.com/watch?v=${v}`;
    }

    // youtube.com/shorts/VIDEO_ID
    if (domain.includes("youtube.com") && parsed.pathname.includes("/shorts/")) {
      const videoId = parsed.pathname.split("/shorts/")[1].split("/")[0].split("?")[0];
      if (videoId) return `https://www.youtube.com/watch?v=${videoId}`;
    }

    // youtube.com/live/VIDEO_ID
    if (domain.includes("youtube.com") && parsed.pathname.includes("/live/")) {
      const videoId = parsed.pathname.split("/live/")[1].split("/")[0].split("?")[0];
      if (videoId) return `https://www.youtube.com/watch?v=${videoId}`;
    }
  } catch (e) {
    // Invalid URL format
  }

  return url;
}

function handleUrlInput() {
  const rawUrl = urlInput.value.trim();

  // Playlist hint
  if (rawUrl.includes("list=") || rawUrl.includes("/playlist")) {
    if (singleVideoCb.checked) {
      urlHint.textContent = "ℹ️ Playlist detected: Downloading single video only.";
    } else {
      urlHint.textContent = "⚠️ Playlist mode ON: Will download entire playlist.";
    }
  } else {
    urlHint.textContent = "";
  }

  // Debounce auto-fetch
  clearTimeout(debounceTimeout);
  if (rawUrl.length >= 15 && (rawUrl.includes("youtube.com") || rawUrl.includes("youtu.be"))) {
    debounceTimeout = setTimeout(() => {
      fetchMetadata();
    }, 700);
  }
}

async function handlePaste() {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      urlInput.value = text.trim();
      handleUrlInput();
      fetchMetadata();
    }
  } catch (err) {
    urlInput.focus();
  }
}

// ---------------- Metadata Fetching ----------------

async function fetchMetadata() {
  const rawUrl = urlInput.value.trim();
  if (!rawUrl) return;

  const isSingle = singleVideoCb.checked;
  const targetUrl = sanitizeYoutubeUrl(rawUrl, isSingle);

  statusTag.textContent = "Fetching info...";
  statusTag.style.background = "rgba(245, 158, 11, 0.15)";
  statusTag.style.color = "#fbbf24";
  videoTitle.textContent = "Fetching video details...";
  btnFetch.disabled = true;

  try {
    const cleanUrl = backendUrl.replace(/\/+$/, "");
    const res = await fetch(`${cleanUrl}/api/info`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: targetUrl, single_video: isSingle })
    });

    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || "Failed to fetch metadata");
    }

    currentVideoInfo = data;
    renderMetadata(data);
  } catch (err) {
    statusTag.textContent = "Error";
    statusTag.style.background = "rgba(239, 68, 68, 0.15)";
    statusTag.style.color = "#f87171";
    videoTitle.textContent = err.message || "Failed to load video.";
  } finally {
    btnFetch.disabled = false;
  }
}

function renderMetadata(info) {
  videoTitle.textContent = info.title || "Unknown Title";
  videoChannel.textContent = `Channel: ${info.uploader || "—"}`;
  videoDuration.textContent = `Duration: ${info.duration_formatted || "—"}`;
  videoViews.textContent = `Views: ${info.view_count_formatted || "—"}`;

  if (info.thumbnail) {
    videoThumbnail.src = info.thumbnail;
    videoThumbnail.style.display = "block";
    thumbPlaceholder.style.display = "none";
  }

  statusTag.textContent = "Ready to download";
  statusTag.style.background = "rgba(34, 197, 94, 0.15)";
  statusTag.style.color = "#4ade80";
}

// ---------------- Download Execution ----------------

async function handleDownload() {
  const rawUrl = urlInput.value.trim();
  if (!rawUrl) {
    alert("Please enter a YouTube video URL first.");
    urlInput.focus();
    return;
  }

  if (isDownloading) return;

  const isSingle = singleVideoCb.checked;
  const targetUrl = sanitizeYoutubeUrl(rawUrl, isSingle);
  const quality = qualitySelect.value;
  const mode = currentMode;

  // UI state
  isDownloading = true;
  btnDownload.disabled = true;
  btnDownloadText.textContent = "Processing Download...";
  progressContainer.style.display = "flex";
  progressBarFill.className = "progress-bar-fill indeterminate";
  progressStatus.textContent = "Downloading & processing stream...";
  progressDetail.textContent = "FFmpeg is converting format";
  resultBox.style.display = "none";

  try {
    const cleanUrl = backendUrl.replace(/\/+$/, "");
    const downloadEndpoint = `${cleanUrl}/api/download?url=${encodeURIComponent(targetUrl)}&mode=${mode}&quality=${quality}&single_video=${isSingle}`;

    // Request download blob
    const response = await fetch(downloadEndpoint, { method: "GET" });
    if (!response.ok) {
      let errText = "Download failed";
      try {
        const errJson = await response.json();
        errText = errJson.error || errText;
      } catch (e) {}
      throw new Error(errText);
    }

    // Determine filename from Content-Disposition header
    let filename = mode === "video" ? "video.mp4" : "audio.mp3";
    const disposition = response.headers.get("Content-Disposition");
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (match && match[1]) {
        filename = match[1].replace(/['"]/g, "");
      }
    } else if (currentVideoInfo && currentVideoInfo.title) {
      const ext = mode === "video" ? ".mp4" : (quality === "m4a" ? ".m4a" : ".mp3");
      filename = `${currentVideoInfo.title.replace(/[\\/:*?"<>|]/g, "_")}${ext}`;
    }

    // Read blob and trigger browser download
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    a.remove();

    // Success UI
    progressContainer.style.display = "none";
    resultBox.style.display = "block";
    resultFilename.textContent = `Saved: ${filename}`;
  } catch (err) {
    progressContainer.style.display = "none";
    alert(`Download Error:\n\n${err.message}\n\nPlease check that your backend server is running and accessible.`);
  } finally {
    isDownloading = false;
    btnDownload.disabled = false;
    btnDownloadText.textContent = "Start Download";
  }
}
