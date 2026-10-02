import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "backend" / "storage"
ARTIFACTS_DIR = STORAGE_DIR / "artifacts"
TEMP_DIR = STORAGE_DIR / "temp"

# Создаем директории при инициализации
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


class AppConfig(BaseModel):
    # Настройки LLM / Ollama
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    default_model: str = os.getenv("DEFAULT_MODEL", "qwen2.5:7b")
    available_models: list[str] = [
        "qwen2.5:7b",
        "qwen2.5:14b",
        "qwen2.5:32b",
        "huihui-ai/Qwen2.5-14B-Instruct-abliterated-GGUF",
        "parable/fable",
        "deepseek-r1:14b",
    ]
    
    # Системные ограничения CPU
    cpu_threads: int = int(os.getenv("CPU_THREADS", "7"))
    context_size: int = int(os.getenv("CONTEXT_SIZE", "8192"))
    
    # Настройки песочницы
    sandbox_timeout: int = int(os.getenv("SANDBOX_TIMEOUT", "35"))
    max_reflection_attempts: int = 3
    
    # Сеть
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))


config = AppConfig()
