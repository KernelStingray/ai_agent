#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

LOGFILE="$DIR/backend/storage/cloudflared.log"
mkdir -p "$DIR/backend/storage"
touch "$LOGFILE"

echo "=========================================================="
echo "   🌐 Запуск Cloudflare Tunnel для OmniAgent Local"
echo "=========================================================="
echo "Локальный адрес: http://localhost:8000"
echo "Логи тоннеля: $LOGFILE"
echo ""

# Проверяем наличие cloudflared
if ! command -v cloudflared &> /dev/null; then
    if [ -f "$HOME/.local/bin/cloudflared" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    else
        echo "❌ Ошибка: cloudflared не найден."
        exit 1
    fi
fi

# Запуск тоннеля
cloudflared tunnel --url http://localhost:8000 --logfile "$LOGFILE"
