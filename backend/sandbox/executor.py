import os
import sys
import time
import shutil
import subprocess
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.config import ARTIFACTS_DIR, TEMP_DIR, config


class CodeExecutor:
    """Безопасный исполнитель Python кода в песочнице с фиксацией созданных файлов."""

    def __init__(self, timeout: Optional[int] = None):
        self.timeout = timeout or config.sandbox_timeout
        self.temp_dir = TEMP_DIR
        self.artifacts_dir = ARTIFACTS_DIR

    def execute(self, code: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Исполняет Python-код во временной изолированной среде.
        Возвращает:
            success: bool
            stdout: str
            stderr: str
            exit_code: int
            execution_time: float
            artifacts: List[Dict[str, Any]] (созданные файлы)
        """
        start_time = time.time()
        sid = session_id or f"run_{int(start_time * 1000)}"
        
        # Создаем изолированную сессионную папку
        run_dir = self.temp_dir / sid
        run_dir.mkdir(parents=True, exist_ok=True)

        script_path = run_dir / "script.py"
        script_path.write_text(code, encoding="utf-8")

        # Фиксируем файлы до запуска
        before_files = {p.name for p in run_dir.rglob("*") if p.is_file()}

        # Подготавливаем окружение для выполнения
        env = os.environ.copy()
        # Добавляем корень проекта и backend в PYTHONPATH, чтобы скрипт мог использовать генераторы
        base_dir = str(Path(__file__).resolve().parent.parent.parent)
        backend_dir = str(Path(base_dir) / "backend")
        env["PYTHONPATH"] = f"{base_dir}:{backend_dir}:{env.get('PYTHONPATH', '')}"
        env["PYTHONIOENCODING"] = "utf-8"
        env["ARTIFACTS_DIR"] = str(self.artifacts_dir)

        try:
            process = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(run_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )
            stdout = process.stdout
            stderr = process.stderr
            exit_code = process.returncode
            success = (exit_code == 0)
        except subprocess.TimeoutExpired:
            stdout = ""
            stderr = f"TimeoutError: Время выполнения превысило лимит {self.timeout} секунд."
            exit_code = -1
            success = False
        except Exception as e:
            stdout = ""
            stderr = f"ExecutionError: {str(e)}"
            exit_code = -1
            success = False

        duration = time.time() - start_time

        # Поиск новых файлов, созданных скриптом (включая подкаталоги)
        after_files = [
            p for p in run_dir.rglob("*")
            if p.is_file() and p.name != "script.py" and not p.name.endswith(".pyc") and "__pycache__" not in p.parts
        ]
        created_artifacts = []

        for path in after_files:
            try:
                name = path.name
                mtime = path.stat().st_mtime
                if name not in before_files or mtime >= (start_time - 1.0):
                    # Перемещаем файл в постоянное хранилище артефактов
                    dest_path = self.artifacts_dir / name
                    shutil.copy2(path, dest_path)
                    
                    size_bytes = dest_path.stat().st_size
                    ext = dest_path.suffix.lower()
                    
                    created_artifacts.append({
                        "filename": name,
                        "filepath": str(dest_path),
                        "size": size_bytes,
                        "size_formatted": self._format_size(size_bytes),
                        "extension": ext,
                        "download_url": f"/api/artifacts/{urllib.parse.quote(name)}",
                    })
            except Exception:
                continue

        # Также проверим файлы, созданные напрямую в ARTIFACTS_DIR
        for p in self.artifacts_dir.glob("*"):
            try:
                if p.is_file() and p.stat().st_mtime >= (start_time - 1.0) and not p.name.startswith("."):
                    if not any(a["filename"] == p.name for a in created_artifacts):
                        size_bytes = p.stat().st_size
                        created_artifacts.append({
                            "filename": p.name,
                            "filepath": str(p),
                            "size": size_bytes,
                            "size_formatted": self._format_size(size_bytes),
                            "extension": p.suffix.lower(),
                            "download_url": f"/api/artifacts/{urllib.parse.quote(p.name)}",
                        })
            except Exception:
                continue

        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "duration": round(duration, 3),
            "artifacts": created_artifacts,
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


executor = CodeExecutor()
