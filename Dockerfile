FROM python:3.14-slim

# Copy the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Bring the toml and lockfile so we can 
# detect drift when running uv sync --frozen
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ .

CMD ["uv", "run", "python", "-u", "main.py"]
