#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "   🚀 Запуск OmniAgent Local & Cloudflare Tunnel в Docker"
echo "=========================================================="

# Подготовка директорий для артефактов и логов
mkdir -p /app/backend/storage/artifacts /app/backend/storage/temp
LOGFILE="/app/backend/storage/cloudflared.log"
touch "$LOGFILE"

PORT="${PORT:-8000}"

# Функция корректной остановки всех процессов
shutdown() {
    echo ""
    echo "🛑 Получен сигнал остановки. Завершение работы сервисов..."
    if [ -n "$CLOUDFLARED_PID" ] && kill -0 "$CLOUDFLARED_PID" 2>/dev/null; then
        echo "   Остановка Cloudflare Tunnel..."
        kill -TERM "$CLOUDFLARED_PID" 2>/dev/null || true
    fi
    if [ -n "$UVICORN_PID" ] && kill -0 "$UVICORN_PID" 2>/dev/null; then
        echo "   Остановка веб-сервера OmniAgent..."
        kill -TERM "$UVICORN_PID" 2>/dev/null || true
    fi
    wait "$UVICORN_PID" 2>/dev/null || true
    wait "$CLOUDFLARED_PID" 2>/dev/null || true
    echo "✅ Все процессы успешно остановлены."
    exit 0
}

trap shutdown SIGTERM SIGINT SIGQUIT

# 1. Запуск FastAPI веб-сервера
echo "📦 Запуск веб-сервера на порту $PORT..."
export PYTHONPATH="/app:$PYTHONPATH"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port "$PORT" &
UVICORN_PID=$!

# Ожидание готовности сервера
echo "⏳ Проверка готовности локального сервера..."
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:$PORT/api/status" > /dev/null 2>&1; then
        echo "✅ Веб-сервер активен и отвечает на запросы."
        break
    fi
    sleep 0.5
done

# 2. Запуск Cloudflare Tunnel
echo "🌐 Запуск Cloudflare Tunnel..."
# Очищаем лог перед новым запуском, чтобы не прочитать ссылку от предыдущей сессии
if [ -f "$LOGFILE" ]; then
    cp "$LOGFILE" "${LOGFILE}.bak" 2>/dev/null || true
    > "$LOGFILE"
fi
cloudflared tunnel --url "http://127.0.0.1:$PORT" --logfile "$LOGFILE" &
CLOUDFLARED_PID=$!

# 3. Извлечение публичной ссылки trycloudflare.com
echo "🔍 Ожидание создания внешнего публичного туннеля..."
TUNNEL_URL=""
for i in $(seq 1 40); do
    if [ -f "$LOGFILE" ]; then
        MATCH=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "$LOGFILE" | tail -n 1 || true)
        if [ -n "$MATCH" ]; then
            TUNNEL_URL="$MATCH"
            break
        fi
    fi
    sleep 0.5
done

echo ""
echo "=========================================================="
echo "   🌟 Сервисы успешно запущены!"
echo "   👉 Локальный адрес: http://localhost:$PORT"
if [ -n "$TUNNEL_URL" ]; then
    echo "   🌍 Публичная ссылка: $TUNNEL_URL"
else
    echo "   ℹ️ Ссылка тоннеля создается. Проверьте: docker compose logs omniagent"
fi
echo "   📁 Артефакты сохраняются в: /app/backend/storage/artifacts"
echo "=========================================================="
echo ""

# Ожидание завершения любого из дочерних процессов
wait -n "$UVICORN_PID" "$CLOUDFLARED_PID" 2>/dev/null || true
shutdown
