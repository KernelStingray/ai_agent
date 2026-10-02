import urllib.parse
from typing import Dict, Any, List
from backend.config import ARTIFACTS_DIR


def get_available_tools_spec() -> List[Dict[str, Any]]:
    """Возвращает спецификацию инструментов для модели (если используется tool calling)."""
    return [
        {
            "name": "execute_python",
            "description": "Выполнить Python код в песочнице для создания файлов или вычислений",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python код для исполнения"}
                },
                "required": ["code"]
            }
        },
        {
            "name": "create_file",
            "description": "Создать произвольный текстовый файл в артефактах",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Имя файла"},
                    "content": {"type": "string", "description": "Текстовое содержимое файла"}
                },
                "required": ["filename", "content"]
            }
        }
    ]


def list_existing_artifacts() -> List[Dict[str, Any]]:
    """Возвращает список всех уже сгенерированных файлов в артефактах."""
    artifacts = []
    files = []
    for p in ARTIFACTS_DIR.glob("*"):
        try:
            if p.is_file() and not p.name.startswith("."):
                files.append((p, p.stat().st_mtime))
        except (OSError, FileNotFoundError):
            continue

    for p, mtime in sorted(files, key=lambda x: x[1], reverse=True):
        try:
            size = p.stat().st_size
            artifacts.append({
                "filename": p.name,
                "size": size,
                "size_formatted": _format_size(size),
                "extension": p.suffix.lower(),
                "created_at": mtime,
                "download_url": f"/api/artifacts/{urllib.parse.quote(p.name)}"
            })
        except (OSError, FileNotFoundError):
            continue
    return artifacts


def _format_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
