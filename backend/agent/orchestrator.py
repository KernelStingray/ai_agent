import json
import re
import asyncio
import httpx
from typing import AsyncGenerator, List, Dict, Any, Optional
from backend.config import config
from backend.agent.prompts import build_system_prompt, REFLECTION_PROMPT_TEMPLATE
from backend.sandbox.executor import executor


class AgentOrchestrator:
    """Оркестратор взаимодействия с локальной LLM, песочницей и обработкой артефактов."""

    def __init__(self):
        self.ollama_base = config.ollama_base_url.rstrip("/")

    async def get_available_models(self) -> List[str]:
        """Запрашивает список установленных моделей из локальной Ollama."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.ollama_base}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m["name"] for m in data.get("models", [])]
                    if models:
                        return models
        except Exception:
            pass
        return config.available_models

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        enable_stealth: bool = True,
        enable_docs: bool = True,
        enable_sandbox: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Асинхронный генератор SSE событий:
        - {"type": "token", "content": "..."}
        - {"type": "status", "message": "..."}
        - {"type": "artifact", "artifact": {...}}
        - {"type": "done"}
        """
        available_models = await self.get_available_models()
        req_model = model or config.default_model
        selected_model = req_model

        # Безопасный выбор модели: если запрошенная отсутствует в Ollama, выбираем существующую
        if available_models and selected_model not in available_models:
            matched = next(
                (m for m in available_models if m.split(":")[0] == selected_model.split(":")[0]),
                available_models[0]
            )
            selected_model = matched

        # Немедленно отправляем статус клиенту для мгновенного старта HTTP/2 SSE стрима в Cloudflare
        yield self._event("status", f"🧠 Подключение к модели {selected_model}...")

        # Подготовка сообщений с системным промптом
        system_prompt = build_system_prompt(enable_stealth=enable_stealth, enable_docs=enable_docs)
        formatted_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m.get("role") in ["user", "assistant"]:
                formatted_messages.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": selected_model,
            "messages": formatted_messages,
            "stream": True,
            "keep_alive": "1h",
            "options": {
                "temperature": 0.85 if enable_stealth else 0.7,
                "num_thread": config.cpu_threads,
                "num_ctx": config.context_size,
            }
        }

        full_response = ""
        ollama_available = True

        # 1. СТРИМИНГ ОТВЕТА МОДЕЛИ С АКТИВНЫМ HEARTBEAT
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=10.0)) as client:
                async with client.stream(
                    "POST",
                    f"{self.ollama_base}/api/chat",
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        yield self._event("token", f"⚠️ Ошибка Ollama (HTTP {response.status_code}): модель `{selected_model}` не смогла запуститься.")
                        yield self._event("done", "")
                        return

                    queue: asyncio.Queue = asyncio.Queue()
                    first_token = True

                    async def stream_reader():
                        try:
                            async for line in response.aiter_lines():
                                await queue.put(line)
                        except Exception as ex:
                            await queue.put(ex)
                        finally:
                            await queue.put(None)

                    reader_task = asyncio.create_task(stream_reader())

                    try:
                        while True:
                            try:
                                item = await asyncio.wait_for(queue.get(), timeout=3.5)
                            except asyncio.TimeoutError:
                                if first_token:
                                    yield self._event("status", f"🧠 Модель {selected_model} анализирует контекст...")
                                else:
                                    yield ": ping\n\n"
                                continue

                            if item is None:
                                break
                            if isinstance(item, Exception):
                                raise item

                            line = item
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                                msg = chunk.get("message", {})
                                content = msg.get("content", "")
                                if content:
                                    if first_token:
                                        first_token = False
                                    full_response += content
                                    yield self._event("token", content)
                            except json.JSONDecodeError:
                                continue
                    finally:
                        if not reader_task.done():
                            reader_task.cancel()

        except httpx.ConnectError:
            ollama_available = False
            err_msg = (
                f"\n\n> ⚠️ **Локальный движок Ollama не обнаружен** по адресу `{self.ollama_base}`.\n"
                f"> Убедитесь, что Ollama запущена командой `ollama serve`, или проверьте настройки в `backend/config.py`."
            )
            yield self._event("token", err_msg)
            yield self._event("done", "")
            return
        except Exception as e:
            yield self._event("token", f"\n\n⚠️ Непредвиденная ошибка соединения: {str(e)}")
            yield self._event("done", "")
            return

        # 2. АНАЛИЗ И ВЫПОЛНЕНИЕ КОДА В ПЕСОЧНИЦЕ (ЕСЛИ ВКЛЮЧЕНО)
        if enable_sandbox and full_response:
            code_blocks = self._extract_code_blocks(full_response)
            
            for code in code_blocks:
                yield self._event("status", "⚡ Запуск кода в изолированной песочнице...")
                
                # Выполнение в sandbox
                result = executor.execute(code)

                # Цикл автоисправления (Reflection Loop) при ошибке
                attempt = 0
                while not result["success"] and attempt < config.max_reflection_attempts and ollama_available:
                    attempt += 1
                    yield self._event("status", f"🔄 Ошибка в коде. Автоисправление (Попытка {attempt}/{config.max_reflection_attempts})...")
                    
                    reflection_prompt = REFLECTION_PROMPT_TEMPLATE.format(
                        error_traceback=result["stderr"],
                        failed_code=code
                    )
                    
                    # Запрос исправленного кода у модели
                    fix_messages = formatted_messages + [
                        {"role": "assistant", "content": full_response},
                        {"role": "user", "content": reflection_prompt}
                    ]
                    
                    corrected_code = await self._get_corrected_code(fix_messages, selected_model)
                    if corrected_code:
                        code = corrected_code
                        result = executor.execute(code)
                    else:
                        break

                # Отправка созданных файлов (артефактов)
                if result["artifacts"]:
                    for art in result["artifacts"]:
                        yield self._event("artifact", art)
                    yield self._event("token", f"\n\n✅ **Файл успешно сформирован:** {len(result['artifacts'])} шт.")
                elif result["success"] and result["stdout"].strip():
                    yield self._event("token", f"\n\n**Результат выполнения в песочнице:**\n```\n{result['stdout'].strip()}\n```")
                elif not result["success"]:
                    yield self._event("token", f"\n\n❌ **Ошибка выполнения скрипта:**\n```\n{result['stderr'].strip()}\n```")

        yield self._event("done", "")

    async def _get_corrected_code(self, messages: List[Dict[str, str]], model: str) -> str:
        """Запрашивает исправленный код у модели для цикла рефлексии."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=10.0)) as client:
                res = await client.post(
                    f"{self.ollama_base}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "keep_alive": "1h",
                        "options": {
                            "temperature": 0.3,
                            "num_thread": config.cpu_threads,
                            "num_ctx": config.context_size,
                        }
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("message", {}).get("content", "")
                    blocks = self._extract_code_blocks(content)
                    if blocks:
                        return blocks[0]
                    # Fallback: любой блок кода в ответе
                    any_blocks = re.findall(r"```(?:python|py)?\b\s*(.*?)(?:```|$)", content, re.DOTALL | re.IGNORECASE)
                    clean_any = [b.strip() for b in any_blocks if b.strip()]
                    if clean_any:
                        return clean_any[0]
                    if "def " in content or "import " in content or "create_" in content:
                        return content.strip()
        except Exception:
            pass
        return ""

    @staticmethod
    def _extract_code_blocks(text: str) -> List[str]:
        """Извлекает блоки кода, помеченные для выполнения (python:execute или содержащие создание файлов)."""
        # 1. Сначала ищем явные блоки python:execute / py:execute / python:run
        explicit_blocks = re.findall(
            r"```(?:python|py)\s*:\s*(?:execute|run|exec)\b\s*(.*?)(?:```|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        explicit_clean = [b.strip() for b in explicit_blocks if b.strip()]
        if explicit_clean:
            return explicit_clean

        # 2. Если явных нет, ищем блоки python/py, где используются генераторы или файловые операции
        all_py = re.findall(r"```(?:python|py)\b\s*(.*?)(?:```|$)", text, re.DOTALL | re.IGNORECASE)
        candidate_blocks = []
        file_keywords = [
            "openpyxl", "docx", "pptx", "reportlab", "create_styled",
            "to_excel", "to_csv", "savefig", "plt.", "matplotlib",
            "with open", "open(", "zipfile", "create_project_zip",
            "pandas", ".save("
        ]
        for b in all_py:
            b_clean = b.strip()
            if not b_clean:
                continue
            if any(k in b_clean for k in file_keywords):
                candidate_blocks.append(b_clean)

        return candidate_blocks

    @staticmethod
    def _event(event_type: str, data: Any) -> str:
        """Форматирует строку события SSE."""
        payload = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
        return f"data: {payload}\n\n"


orchestrator = AgentOrchestrator()
