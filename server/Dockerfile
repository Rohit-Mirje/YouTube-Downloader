FROM python:3.11-slim

# Install FFmpeg and Node.js (required by yt-dlp for signature / stream deciphering)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Expose port (Render/Hugging Face uses PORT or default 5000/7860)
ENV PORT=5000
EXPOSE 5000

# Run with Gunicorn production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "300", "server:app"]
