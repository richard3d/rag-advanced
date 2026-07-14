FROM ghcr.io/berriai/litellm:main-latest

RUN apk update && apk add --no-cache \
    uv
# The ollama vision provider needs Pillow to convert images, but the base
# image doesn't ship it.w
RUN uv pip install --no-cache-dir pillow

