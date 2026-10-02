import os
import re
import psutil
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import config, ARTIFACTS_DIR, BASE_DIR, STORAGE_DIR
from backend.agent.orchestrator import orchestrator
from backend.agent.tools import list_existing_artifacts

app = FastAPI(title="OmniAgent Local", version="1.0.0")

# CORS для локальной разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    enable_stealth: bool = True
    enable_docs: bool = True
    enable_sandbox: bool = True


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Стриминг диалога с агентом через Server-Sent Events (SSE)."""
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    
    stream_generator = orchestrator.stream_chat(
        messages=messages,
        model=req.model,
        enable_stealth=req.enable_stealth,
        enable_docs=req.enable_docs,
        enable_sandbox=req.enable_sandbox,
    )

    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/models")
async def get_models():
    """Возвращает список доступных моделей в системе."""
    models = await orchestrator.get_available_models()
    default_m = config.default_model if config.default_model in models else (models[0] if models else config.default_model)
    return {"models": models, "default": default_m}


@app.get("/api/artifacts")
async def get_artifacts():
    """Возвращает список всех созданных файлов."""
    return {"artifacts": list_existing_artifacts()}


@app.get("/api/artifacts/{filename}")
async def download_artifact(filename: str):
    """Скачивание сгенерированного файла."""
    safe_name = os.path.basename(filename)
    filepath = ARTIFACTS_DIR / safe_name
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(
        path=str(filepath),
        filename=safe_name,
        media_type="application/octet-stream"
    )


def get_active_tunnel_url() -> Optional[str]:
    """Извлекает последнюю актуальную ссылку trycloudflare.com из логов туннеля."""
    logfile = STORAGE_DIR / "cloudflared.log"
    if not logfile.exists():
        return None
    try:
        with open(logfile, "rb") as f:
            f.seek(max(0, logfile.stat().st_size - 64 * 1024))
            tail = f.read().decode("utf-8", errors="ignore")
        matches = re.findall(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", tail)
        return matches[-1] if matches else None
    except Exception:
        return None


@app.get("/api/status")
async def get_system_status():
    """Возвращает текущую нагрузку на процессор, использование ОЗУ и статус туннеля."""
    vm = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=None)
    
    return {
        "cpu": {
            "percent": cpu_pct,
            "threads_allocated": config.cpu_threads,
            "total_cores": psutil.cpu_count(logical=True),
        },
        "memory": {
            "total_gb": round(vm.total / (1024 ** 3), 1),
            "available_gb": round(vm.available / (1024 ** 3), 1),
            "used_gb": round(vm.used / (1024 ** 3), 1),
            "percent": vm.percent,
        },
        "artifacts_count": len(list(ARTIFACTS_DIR.glob("*"))),
        "sandbox_timeout": config.sandbox_timeout,
        "tunnel_url": get_active_tunnel_url(),
    }


# Монтирование статики фронтенда
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=config.host, port=config.port, reload=True)
