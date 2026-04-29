FROM python:3.11-slim
WORKDIR /app

# Playwright Chromium 所需系統套件
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY sneaker-pricing/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && playwright install chromium --with-deps

COPY sneaker-pricing/ .
CMD ["/bin/bash", "-c", "cd sneaker-web && uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
