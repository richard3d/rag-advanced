FROM python:3.14-slim

# Copy the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Runtime .so deps for opencv-python (pulled in by docling's rapidocr OCR
# engine). The slim base image lacks these X11/GL libs that cv2 needs
# even when no display is attached.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bring the toml and lockfile so we can 
# detect drift when running uv sync --frozen
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ .

CMD ["uv", "run", "python", "-u", "main.py"]
