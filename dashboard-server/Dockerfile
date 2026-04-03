# ── Base runtime image (bash + uv + playwright deps) ──────────────────────────
FROM astral/uv:python3.12-bookworm-slim

# Install bash, system deps for Playwright/Chromium, and timezone support
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    tzdata \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Shanghai \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENV=/app/venv

WORKDIR /app

# Install project base dependencies into /app/venv without copying source code
COPY pyproject.toml uv.lock ./
RUN uv venv /app/venv \
    && uv sync --frozen --no-dev --no-install-project

# Preinstall Playwright Chromium using the venv
RUN uv run playwright install chromium --with-deps

CMD ["/bin/bash"]
