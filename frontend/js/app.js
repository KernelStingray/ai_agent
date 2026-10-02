/**
 * OmniAgent Local — Главный скрипт веб-приложения
 */

const App = {
  conversationHistory: [],
  isGenerating: false,

  init() {
    window.ChatManager.init();
    window.ArtifactsManager.init();
    this.bindEvents();
    this.loadModels();
    this.updateSystemStatus();
    setInterval(() => this.updateSystemStatus(), 4000);
  },

  bindEvents() {
    const sendBtn = document.getElementById('send-btn');
    const promptInput = document.getElementById('user-prompt');
    const clearBtn = document.getElementById('clear-chat-btn');

    if (sendBtn) {
      sendBtn.addEventListener('click', () => this.sendMessage());
    }

    if (promptInput) {
      promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });

      // Авто-регулировка высоты textarea
      promptInput.addEventListener('input', () => {
        promptInput.style.height = 'auto';
        promptInput.style.height = Math.min(promptInput.scrollHeight, 180) + 'px';
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        this.conversationHistory = [];
        window.ChatManager.clearChat();
      });
    }

    // Привязка кликов по подсказкам
    window.ChatManager.bindQuickChips();
  },

  async loadModels() {
    try {
      const res = await fetch('/api/models');
      if (res.ok) {
        const data = await res.json();
        const select = document.getElementById('model-select');
        if (select && data.models && data.models.length > 0) {
          select.innerHTML = data.models.map(m => `
            <option value="${m}" ${m === data.default ? 'selected' : ''}>${m}</option>
          `).join('');
        }
      }
    } catch (err) {
      console.warn('Не удалось загрузить список моделей:', err);
    }
  },

  async updateSystemStatus() {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        const statusText = document.getElementById('status-text');
        if (statusText) {
          statusText.textContent = `CPU: ${data.cpu.percent}% | RAM: ${data.memory.used_gb} / ${data.memory.total_gb} GB (${data.memory.percent}%)`;
        }

        const tunnelLink = document.getElementById('tunnel-link');
        const tunnelText = document.getElementById('tunnel-text');
        if (tunnelLink) {
          if (data.tunnel_url) {
            tunnelLink.classList.remove('hidden');
            tunnelLink.href = data.tunnel_url;
            if (tunnelText) {
              const shortUrl = data.tunnel_url.replace('https://', '').replace('.trycloudflare.com', '');
              tunnelText.textContent = `🌐 ${shortUrl}`;
            }
            tunnelLink.title = `Публичный доступ через Cloudflare Tunnel: ${data.tunnel_url}`;
          } else {
            tunnelLink.classList.add('hidden');
          }
        }
      }
    } catch (err) {
      // Игнорируем сетевые сбои поллинга
    }
  },

  async sendMessage() {
    const input = document.getElementById('user-prompt');
    const text = input ? input.value.trim() : '';
    if (!text || this.isGenerating) return;

    this.isGenerating = true;
    input.value = '';
    input.style.height = 'auto';
    this.toggleInputs(false);

    // Добавляем сообщение пользователя в UI и историю
    window.ChatManager.addUserMessage(text);
    this.conversationHistory.push({ role: 'user', content: text });

    // Создаем пузырь для ответа
    window.ChatManager.createAssistantMessage();

    // Считываем настройки тумблеров
    const enableDocs = document.getElementById('toggle-docs')?.checked ?? true;
    const enableSandbox = document.getElementById('toggle-sandbox')?.checked ?? true;
    const enableStealth = document.getElementById('toggle-stealth')?.checked ?? true;
    const selectedModel = document.getElementById('model-select')?.value || null;

    const statusBar = document.getElementById('agent-status-bar');
    const statusText = document.getElementById('agent-status-text');

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: this.conversationHistory,
          model: selectedModel,
          enable_docs: enableDocs,
          enable_sandbox: enableSandbox,
          enable_stealth: enableStealth,
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ошибка: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let assistantFullText = "";
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Сохраняем неполную строку

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;
          const jsonStr = trimmed.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const event = JSON.parse(jsonStr);

            if (event.type === 'token') {
              if (statusBar && !statusBar.classList.contains('hidden')) {
                statusBar.classList.add('hidden');
              }
              assistantFullText += event.data;
              window.ChatManager.appendToken(event.data);
            } else if (event.type === 'status') {
              if (statusBar && statusText) {
                statusBar.classList.remove('hidden');
                statusText.textContent = event.data;
              }
              window.ArtifactsManager.logConsole(`[STATUS] ${event.data}`);
            } else if (event.type === 'artifact') {
              window.ArtifactsManager.addArtifact(event.data);
              window.ArtifactsManager.logConsole(`[ARTIFACT] Создан файл: ${event.data.filename} (${event.data.size_formatted})`);
            } else if (event.type === 'done') {
              if (statusBar) statusBar.classList.add('hidden');
            }
          } catch (e) {
            console.error('Ошибка парсинга SSE:', e, jsonStr);
          }
        }
      }

      if (assistantFullText) {
        this.conversationHistory.push({ role: 'assistant', content: assistantFullText });
      }

    } catch (err) {
      window.ChatManager.appendToken(`\n\n⚠️ **Ошибка подключения:** ${err.message}`);
    } finally {
      if (statusBar) statusBar.classList.add('hidden');
      window.ChatManager.finishAssistantMessage();
      this.isGenerating = false;
      this.toggleInputs(true);
      input.focus();
    }
  },

  toggleInputs(enabled) {
    const sendBtn = document.getElementById('send-btn');
    const input = document.getElementById('user-prompt');
    if (sendBtn) sendBtn.disabled = !enabled;
    if (input) input.disabled = !enabled;
  }
};

document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
