/**
 * OmniAgent Local — Управление панелью артефактов и файлов
 */

const ArtifactsManager = {
  artifacts: [],

  init() {
    this.bindEvents();
    this.fetchArtifacts();
  },

  bindEvents() {
    const refreshBtn = document.getElementById('refresh-artifacts-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.fetchArtifacts());
    }

    // Переключение табов в панели артефактов
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        tabBtns.forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));

        btn.classList.add('active');
        const targetTabId = btn.getAttribute('data-tab');
        const targetTab = document.getElementById(targetTabId);
        if (targetTab) {
          targetTab.classList.add('active');
        }
      });
    });
  },

  async fetchArtifacts() {
    try {
      const res = await fetch('/api/artifacts');
      if (res.ok) {
        const data = await res.json();
        this.artifacts = data.artifacts || [];
        this.renderArtifacts();
      }
    } catch (err) {
      console.warn('Не удалось загрузить артефакты:', err);
    }
  },

  addArtifact(artifact) {
    // Проверяем, нет ли уже такого файла
    const exists = this.artifacts.some(a => a.filename === artifact.filename);
    if (!exists) {
      this.artifacts.unshift(artifact);
      this.renderArtifacts();
      // Автоматически переключаем на таб файлов
      const tabFilesBtn = document.getElementById('tab-btn-files');
      if (tabFilesBtn) tabFilesBtn.click();
    }
  },

  renderArtifacts() {
    const container = document.getElementById('artifacts-list');
    const badge = document.getElementById('artifacts-badge');
    if (!container) return;

    if (badge) {
      badge.textContent = this.artifacts.length;
    }

    if (this.artifacts.length === 0) {
      container.innerHTML = `
        <div class="empty-artifacts-state" id="empty-artifacts-msg">
          <div class="empty-icon">📂</div>
          <p>Здесь появятся сгенерированные файлы (Excel, Word, PowerPoint, PDF, ZIP).</p>
        </div>
      `;
      return;
    }

    container.innerHTML = this.artifacts.map(art => this.createCardHtml(art)).join('');
  },

  createCardHtml(art) {
    const ext = (art.extension || '').replace('.', '').toLowerCase();
    let badgeClass = 'code';
    let label = ext.toUpperCase() || 'FILE';

    if (['xlsx', 'xls', 'csv'].includes(ext)) {
      badgeClass = 'xlsx';
      label = 'XLSX';
    } else if (['docx', 'doc'].includes(ext)) {
      badgeClass = 'docx';
      label = 'DOCX';
    } else if (['pptx', 'ppt'].includes(ext)) {
      badgeClass = 'pptx';
      label = 'PPTX';
    } else if (ext === 'pdf') {
      badgeClass = 'pdf';
      label = 'PDF';
    } else if (['zip', 'tar', 'gz'].includes(ext)) {
      badgeClass = 'zip';
      label = 'ZIP';
    }

    const downloadUrl = art.download_url || `/api/artifacts/${art.filename}`;
    const sizeStr = art.size_formatted || (art.size ? `${Math.round(art.size / 1024)} KB` : '');

    return `
      <div class="artifact-card" data-filename="${art.filename}">
        <div class="artifact-badge-icon ${badgeClass}">${label}</div>
        <div class="artifact-info">
          <div class="artifact-name" title="${art.filename}">${art.filename}</div>
          <div class="artifact-meta">${sizeStr} • Готов к скачиванию</div>
        </div>
        <a href="${downloadUrl}" download="${art.filename}" class="download-btn" title="Скачать файл">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Скачать
        </a>
      </div>
    `;
  },

  logConsole(text) {
    const consoleEl = document.getElementById('sandbox-log-output');
    if (consoleEl) {
      consoleEl.textContent += `\n[${new Date().toLocaleTimeString()}] ${text}`;
      consoleEl.scrollTop = consoleEl.scrollHeight;
    }
  }
};

window.ArtifactsManager = ArtifactsManager;
