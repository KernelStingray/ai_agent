FROM python:3.11-slim

# Установка системных зависимостей:
# - curl и ca-certificates для загрузки cloudflared и healthcheck
# - fonts-dejavu-core для поддержки кириллицы в генерируемых PDF файлах (ReportLab)
# - procps для psutil (мониторинг процессора и памяти)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    fonts-dejavu-core \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Установка бинарника Cloudflare Tunnel (cloudflared)
RUN curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared \
    && chmod +x /usr/local/bin/cloudflared

WORKDIR /app

# Установка Python-зависимостей (кэшируем слой)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходных файлов приложения
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Настройки переменных окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV OLLAMA_BASE_URL=http://127.0.0.1:11434
ENV HOST=0.0.0.0
ENV PORT=8000

# Создание директории под артефакты
RUN mkdir -p /app/backend/storage/artifacts /app/backend/storage/temp

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
