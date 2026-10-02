#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

ACTION="${1:-up}"

echo "=========================================================="
echo "   🐳 OmniAgent Local Docker Manager"
echo "=========================================================="

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Ошибка: Docker не установлен или не найден в PATH."
    exit 1
fi

case "$ACTION" in
    up|start)
        # Проверка доступности Ollama на хосте
        echo "🔍 Проверка подключения к Ollama (http://localhost:11434)..."
        if curl -s --connect-timeout 2 http://localhost:11434/api/tags > /dev/null; then
            echo "✅ Движок Ollama активен и доступен!"
        else
            echo "⚠️ Внимание: Ollama не отвечает на http://localhost:11434."
            echo "   Убедитесь, что модель или служба Ollama запущена на хосте."
        fi

        echo ""
        echo "🏗️ Сборка и запуск контейнера в фоновом режиме..."
        docker compose up --build -d

        echo ""
        echo "⏳ Ожидание старта сервисов и получения ссылки Cloudflare..."
        LOGFILE="$DIR/backend/storage/cloudflared.log"
        TUNNEL_URL=""
        for i in $(seq 1 30); do
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
        echo "   🌟 OmniAgent Local успешно развернут!"
        echo "   👉 Локальный адрес: http://localhost:8000"
        if [ -n "$TUNNEL_URL" ]; then
            echo "   🌍 Публичная ссылка: $TUNNEL_URL"
        else
            echo "   ℹ️ Ссылка еще формируется. Проверьте: ./docker-run.sh logs"
        fi
        echo "=========================================================="
        echo "📜 Просмотр логов:   ./docker-run.sh logs"
        echo "🛑 Остановка:        ./docker-run.sh down"
        echo "=========================================================="
        ;;

    logs)
        docker compose logs -f omniagent
        ;;

    down|stop)
        echo "🛑 Остановка контейнера OmniAgent..."
        docker compose down
        echo "✅ Контейнер остановлен."
        ;;

    restart)
        echo "🔄 Перезапуск контейнера..."
        docker compose restart
        docker compose logs --tail=20 -f omniagent
        ;;

    *)
        echo "Использование: $0 [up|logs|down|restart]"
        exit 1
        ;;
esac
