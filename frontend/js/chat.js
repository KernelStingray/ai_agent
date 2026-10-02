/**
 * OmniAgent Local — Управление окном диалога и Markdown рендерингом
 */

const ChatManager = {
  container: null,
  currentAssistantBubble: null,
  currentRawText: "",

  init() {
    this.container = document.getElementById('messages-container');
    this.setupMarked();
  },

  setupMarked() {
    if (window.marked) {
      marked.setOptions({
        breaks: true,
        gfm: true,
        highlight: function (code, lang) {
          if (window.hljs) {
            const cleanLang = (lang || '').split(':')[0].trim().toLowerCase();
            const language = hljs.getLanguage(cleanLang) ? cleanLang : (cleanLang === 'py' ? 'python' : 'plaintext');
            try {
              return hljs.highlight(code, { language }).value;
            } catch (e) {
              return code;
            }
          }
          return code;
        }
      });
    }
  },

  addUserMessage(text) {
    this.hideWelcome();
    const row = document.createElement('div');
    row.className = 'message-row user';
    row.innerHTML = `
      <div class="message-avatar">Вы</div>
      <div class="message-bubble">${this.escapeHtml(text).replace(/\n/g, '<br>')}</div>
    `;
    this.container.appendChild(row);
    this.scrollToBottom();
  },

  createAssistantMessage() {
    this.hideWelcome();
    this.currentRawText = "";

    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.innerHTML = `
      <div class="message-avatar">⚡</div>
      <div class="message-bubble">
        <div class="stream-content"></div>
      </div>
    `;
    this.container.appendChild(row);
    this.currentAssistantBubble = row.querySelector('.stream-content');
    this.scrollToBottom();
    return this.currentAssistantBubble;
  },

  appendToken(token) {
    if (!this.currentAssistantBubble) return;
    this.currentRawText += token;

    if (window.marked) {
      this.currentAssistantBubble.innerHTML = marked.parse(this.currentRawText);
      this.currentAssistantBubble.querySelectorAll('pre code').forEach((el) => {
        if (window.hljs) hljs.highlightElement(el);
      });
    } else {
      this.currentAssistantBubble.textContent = this.currentRawText;
    }

    this.scrollToBottom();
  },

  finishAssistantMessage() {
    if (this.currentAssistantBubble) {
      this.addCopyButtons(this.currentAssistantBubble);
    }
    this.currentAssistantBubble = null;
    this.currentRawText = "";
  },

  addCopyButtons(bubble) {
    const pres = bubble.querySelectorAll('pre');
    pres.forEach(pre => {
      if (pre.querySelector('.copy-code-btn')) return;

      const btn = document.createElement('button');
      btn.className = 'copy-code-btn';
      btn.textContent = 'Копировать';
      btn.style.position = 'absolute';
      btn.style.top = '6px';
      btn.style.right = '6px';
      btn.style.fontSize = '0.7rem';
      btn.style.padding = '3px 8px';
      btn.style.background = '#1e222d';
      btn.style.color = '#94a3b8';
      btn.style.border = '1px solid #363e56';
      btn.style.borderRadius = '4px';
      btn.style.cursor = 'pointer';

      btn.addEventListener('click', () => {
        const code = pre.querySelector('code')?.innerText || pre.innerText;
        navigator.clipboard.writeText(code).then(() => {
          btn.textContent = 'Скопировано!';
          setTimeout(() => { btn.textContent = 'Копировать'; }, 2000);
        });
      });

      pre.style.position = 'relative';
      pre.appendChild(btn);
    });
  },

  hideWelcome() {
    const welcome = document.getElementById('welcome-message');
    if (welcome) {
      welcome.style.display = 'none';
    }
  },

  clearChat() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="welcome-card" id="welcome-message">
        <div class="welcome-icon">✨</div>
        <h2>Добро пожаловать в OmniAgent Local</h2>
        <p>Ваша персональная автономная AI-станция. Работает полностью локально, без цензуры, логов и ограничений.</p>
        <div class="quick-prompts-grid">
          <button class="quick-chip" data-prompt="Создай финансовую модель расходов и доходов стартапа в таблице Excel (.xlsx) с формулами, графиком и стилизацией">
            📊 Финансовая модель в Excel (.xlsx)
          </button>
          <button class="quick-chip" data-prompt="Подготовь развернутый структурированный отчет по оптимизации серверной инфраструктуры в формате Word (.docx) с таблицами">
            📝 Аналитический отчет в Word (.docx)
          </button>
          <button class="quick-chip" data-prompt="Сделай стильную презентацию 16:9 (.pptx) из 4 слайдов на тему Архитектура автономных ИИ-агентов">
            📽️ Презентация 16:9 (.pptx)
          </button>
          <button class="quick-chip" data-prompt="Напиши микросервис на Python FastAPI с Dockerfile, docker-compose.yml и упакуй всё в готовый .zip архив">
            📦 Полный проект с Docker в .zip
          </button>
        </div>
      </div>
    `;
    this.bindQuickChips();
  },

  bindQuickChips() {
    const chips = document.querySelectorAll('.quick-chip');
    chips.forEach(chip => {
      chip.addEventListener('click', () => {
        const promptText = chip.getAttribute('data-prompt');
        const input = document.getElementById('user-prompt');
        if (input) {
          input.value = promptText;
          document.getElementById('send-btn')?.click();
        }
      });
    });
  },

  scrollToBottom() {
    if (this.container) {
      this.container.scrollTop = this.container.scrollHeight;
    }
  },

  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
};

window.ChatManager = ChatManager;
