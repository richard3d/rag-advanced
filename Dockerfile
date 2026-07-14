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

# Bake docling model weights into image so we do not
# need to reach out to Hugging Face during each startup
RUN uv run docling-tools models download
ENV DOCLING_ARTIFACTS_PATH=/root/.cache/docling/models

# HybridChunker pulls its own tokenizer separately from the models above,
# so bake that in too to avoid Hugging Face Hub calls during chunking
ENV HF_HOME=/opt/hf-cache
# Note: This python import statement is what triggers the download rather than
# It's a little hacky but it makes it so we do not need to download the Hugging Face
# CLI as well.
RUN uv run python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')"

COPY src/ .

CMD ["uv", "run", "python", "-u", "main.py"]
