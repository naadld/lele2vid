FROM python:3.12-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Install system dependencies for Manim, FFmpeg, Cairo, Pango, and CJK fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    pkg-config \
    gcc \
    g++ \
    fontconfig \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    ca-certificates \
    curl \
    && fc-cache -f -v \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and scripts
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY assets/ /app/assets/
COPY data/ /app/data/
COPY configs/ /app/configs/
COPY tiktok_hsk.py /app/
COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Create output directories
RUN mkdir -p /app/output/videos /app/output/metadata /app/output/generated_scenes /app/output/media

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["video-gen"]
