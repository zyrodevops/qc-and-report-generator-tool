FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies:
# - curl for healthcheck
# - libreoffice-core & libreoffice-writer for headless DOCX->PDF rendering (CRITICAL-RULES §7)
# - antiword for legacy .doc binary parsing
# - gcc and libpq-dev for database driver compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libreoffice-core \
    libreoffice-writer \
    antiword \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/storage/uploads /app/storage/derived /app/templates

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
