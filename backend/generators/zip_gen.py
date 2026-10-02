import zipfile
from pathlib import Path
from typing import Dict, Union


def create_project_zip(
    zip_filepath: str,
    files_dict: Dict[str, Union[str, bytes]],
) -> str:
    """
    Создает .zip архив проекта из словаря {путь_к_файлу: содержимое}.
    files_dict = {
        "backend/main.py": "import fastapi...",
        "Dockerfile": "FROM python:3.12...",
        "README.md": "# My App..."
    }
    """
    out_path = Path(zip_filepath)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path, content in files_dict.items():
            # Нормализация пути внутри zip-архива
            clean_rel_path = str(rel_path).lstrip("/\\").replace("\\", "/")
            if isinstance(content, str):
                zf.writestr(clean_rel_path, content.encode("utf-8"))
            else:
                zf.writestr(clean_rel_path, content)

    return str(out_path)
