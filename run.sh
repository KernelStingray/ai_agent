#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "   🚀 Запуск OmniAgent Local (Автономная AI-станция)"
echo "=========================================================="

# 1. Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Ошибка: python3 не найден в системе."
    exit 1
fi

PYTHON_VER=$(python3 --version)
echo "✅ Python обнаружен: $PYTHON_VER"

# 2. Проверка установленных пакетов
echo "🔍 Проверка библиотек Python..."
if ! python3 -c "import fastapi, uvicorn, openpyxl, docx, pptx, reportlab, pandas" &> /dev/null; then
    echo "📦 Установка недостающих зависимостей из requirements.txt..."
    pip install --user -r requirements.txt --break-system-packages
fi
echo "✅ Все необходимые библиотеки готовы."

# 3. Проверка доступности локального движка Ollama
echo "🔌 Проверка подключения к Ollama (http://localhost:11434)..."
if curl -s --connect-timeout 2 http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Движок Ollama активен и доступен!"
else
    echo "⚠️ Внимание: Ollama сейчас не запущена или недоступна на порту 11434."
    echo "   Чтобы запустить модель, выполните в отдельном терминале:"
    echo "   ollama run qwen2.5:14b  (или ollama serve)"
fi

# 4. Проверка занятости порта 8000
if curl -s --connect-timeout 1 http://localhost:8000/api/status > /dev/null 2>&1; then
    echo ""
    echo "=========================================================="
    echo "   ⚡ OmniAgent УЖЕ запущен и работает (например, в Docker)!"
    echo "   👉 http://localhost:8000"
    echo "=========================================================="
    echo "   Чтобы остановить Docker-версию: ./docker-run.sh down"
    echo "   Чтобы посмотреть логи туннеля:  ./docker-run.sh logs"
    echo ""
    exit 0
fi

# 5. Запуск FastAPI веб-сервера
echo ""
echo "=========================================================="
echo "   🌐 Сервер запущен и доступен по адресу:"
echo "   👉 http://localhost:8000"
echo "=========================================================="
echo "Нажмите Ctrl + C для остановки сервера."
echo ""

export PYTHONPATH="$DIR:$PYTHONPATH"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
