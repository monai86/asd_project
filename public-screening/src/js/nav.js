/**
 * nav.js — Shared Navigation & AppShell Component
 *
 * Injects a modern sidebar navigation menu and a dynamic top bar into every page.
 * Handles theme toggling, language switching, help dialogs, and mobile drawers.
 */

import { getCurrentLang, setLang, t } from './i18n.js';

// ─── Page-path detection ────────────────────────────────────────────────────
const PAGE_LINKS = [
  { key: 'home',      href: 'index.html',      i18n: 'nav.home',      icon: '🏠' },
  { key: 'screening', href: 'screening.html',   i18n: 'nav.screening', icon: '📋' },
  { key: 'results',   href: 'results.html',     i18n: 'nav.results',   icon: '📊' },
  { key: 'education', href: 'education.html',   i18n: 'nav.education', icon: '📖' },
  { key: 'resources', href: 'resources.html',   i18n: 'nav.resources', icon: '📎' },
  { key: 'about',     href: 'about.html',       i18n: 'nav.about',     icon: 'ℹ️' },
  { key: 'profile',   href: 'profile.html',     i18n: 'nav.profile',   icon: '👤' },
  { key: 'settings',  href: 'settings.html',    i18n: 'nav.settings',  icon: '⚙️' },
];

/**
 * Determine which page key is currently active based on pathname.
 */
function getActivePage() {
  const path = window.location.pathname.toLowerCase();
  if (path.includes('screening'))  return 'screening';
  if (path.includes('results'))    return 'results';
  if (path.includes('education'))  return 'education';
  if (path.includes('resources'))  return 'resources';
  if (path.includes('about'))      return 'about';
  if (path.includes('profile'))    return 'profile';
  if (path.includes('settings'))   return 'settings';
  return 'home';
}

/**
 * Initialize theme setting from localStorage.
 */
function initTheme() {
  const currentTheme = localStorage.getItem('asd-theme') || 'light';
  if (currentTheme === 'dark') {
    document.body.classList.add('dark');
  } else {
    document.body.classList.remove('dark');
  }
}

/**
 * Build the top bar HTML dynamically based on the current page context.
 */
function buildTopBarHTML() {
  const activePage = getActivePage();
  const pageTitle = t(`nav.${activePage}`) || 'Dashboard';
  const lang = getCurrentLang();
  const toggleLabel = lang === 'en' ? '🌐 TH' : '🌐 EN';

  return `
    <div class="top-bar-left">
      <span class="top-bar-title" data-i18n="nav.${activePage}">${pageTitle}</span>
    </div>
    <div class="top-bar-right">
      <!-- Help Trigger -->
      <button class="top-bar-btn" id="btn-help" title="${t('nav.help') || 'Help'}">
        <span>❓</span> <span data-i18n="nav.help">${t('nav.help') || 'Help'}</span>
      </button>
      <!-- Dark Mode Toggle -->
      <button class="top-bar-btn" id="btn-theme-toggle" title="Toggle Theme" aria-label="Toggle Theme">
        🌓
      </button>
      <!-- Language Selector -->
      <button class="top-bar-btn lang-toggle" data-lang-toggle aria-label="Switch language">
        ${toggleLabel}
      </button>
      <!-- Login Button -->
      <button class="btn btn-primary login-btn" id="btn-login" data-i18n="nav.login">
        ${t('nav.login') || 'Sign In'}
      </button>
    </div>
  `;
}

/**
 * Build the sidebar HTML string.
 */
function buildNavHTML() {
  const activePage = getActivePage();
  const lang = getCurrentLang();
  const toggleLabel = lang === 'en' ? '🌐 TH' : '🌐 EN';

  const links = PAGE_LINKS.map(({ key, href, i18n, icon }) => {
    const activeClass = key === activePage ? ' active' : '';
    return `
      <a href="${href}" class="sidebar-link${activeClass}" data-i18n="${i18n}">
        <span class="sidebar-link-icon">${icon}</span>
        <span class="sidebar-link-text">${t(i18n)}</span>
      </a>
    `;
  }).join('');

  return `
    <!-- Mobile header bar -->
    <header class="mobile-header hide-desktop">
      <button class="nav-toggle" aria-label="Toggle menu" aria-expanded="false">
        <span></span>
        <span></span>
        <span></span>
      </button>
      <a href="index.html" class="mobile-logo">asd-Project</a>
    </header>

    <!-- Sidebar Navigation -->
    <aside class="sidebar" role="navigation" aria-label="Main navigation">
      <!-- Logo block -->
      <div class="sidebar-brand-wrapper">
        <div class="sidebar-logo-icon">💜</div>
        <a href="index.html" class="sidebar-brand">
          <span class="brand-title">asd-Project</span>
          <span class="brand-subtitle" data-i18n="nav.brandSubtitle">${t('nav.brandSubtitle')}</span>
        </a>
      </div>

      <!-- Links list -->
      <nav class="sidebar-menu">
        ${links}
      </nav>

      <!-- Sidebar footer widget -->
      <div class="sidebar-widget">
        <img src="/images/mascot_brain.png" alt="Brain Mascot" class="sidebar-widget-img" />
        <p class="sidebar-widget-text" data-i18n="nav.widgetText">${t('nav.widgetText')}</p>
        <span class="sidebar-widget-subtext" data-i18n="nav.widgetSubtext">${t('nav.widgetSubtext')}</span>
      </div>

      <!-- Optional language switcher fallback for accessibility -->
      <div class="sidebar-footer" style="display: none;">
        <button class="lang-toggle" data-lang-toggle aria-label="Switch language">
          ${toggleLabel}
        </button>
      </div>
    </aside>
  `;
}

/**
 * Refresh text content inside all elements carrying translation attributes.
 */
function refreshNavText() {
  const lang = getCurrentLang();

  // Update data-i18n elements on the entire page
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const translated = t(el.dataset.i18n);
    if (translated.includes('<') || translated.includes('&')) {
      el.innerHTML = translated;
    } else {
      el.textContent = translated;
    }
  });

  // Links have inner tags, refresh their text while preserving icons
  PAGE_LINKS.forEach(({ href, i18n, icon }) => {
    const link = document.querySelector(`.sidebar a[href="${href}"]`);
    if (link) {
      link.innerHTML = `
        <span class="sidebar-link-icon">${icon}</span>
        <span class="sidebar-link-text">${t(i18n)}</span>
      `;
    }
  });

  // Update all lang toggle buttons (sidebar and top bar)
  document.querySelectorAll('[data-lang-toggle]').forEach(toggle => {
    toggle.textContent = lang === 'en' ? '🌐 TH' : '🌐 EN';
  });
}

/**
 * Bind hamburger toggle, language selector, dark mode toggle, and help/login buttons.
 */
function bindNavEvents() {
  const container = document.getElementById('nav-container');
  if (!container) return;

  // ── Hamburger toggle ──
  const hamburger = container.querySelector('.nav-toggle');
  const sidebar = container.querySelector('.sidebar');

  if (hamburger && sidebar) {
    hamburger.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = sidebar.classList.toggle('open');
      hamburger.classList.toggle('active', isOpen);
      hamburger.setAttribute('aria-expanded', String(isOpen));
    });

    sidebar.querySelectorAll('.sidebar-link').forEach((link) => {
      link.addEventListener('click', () => {
        sidebar.classList.remove('open');
        hamburger.classList.remove('active');
        hamburger.setAttribute('aria-expanded', 'false');
      });
    });

    document.addEventListener('click', (e) => {
      if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && !hamburger.contains(e.target)) {
        sidebar.classList.remove('open');
        hamburger.classList.remove('active');
        hamburger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ── Language toggles ──
  document.querySelectorAll('[data-lang-toggle]').forEach(langBtn => {
    langBtn.addEventListener('click', () => {
      const next = getCurrentLang() === 'en' ? 'th' : 'en';
      setLang(next);
      refreshNavText();
    });
  });

  // ── Theme toggle ──
  const themeToggle = document.getElementById('btn-theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const isDark = document.body.classList.toggle('dark');
      localStorage.setItem('asd-theme', isDark ? 'dark' : 'light');
    });
  }

  // ── Help button ──
  const helpBtn = document.getElementById('btn-help');
  if (helpBtn) {
    helpBtn.addEventListener('click', () => {
      alert(getCurrentLang() === 'en' ? 
        "Need help? Contact our clinical screening support team at support@asd-project.org or read the About / Safety Page." : 
        "ต้องการความช่วยเหลือ? ติดต่อทีมสนับสนุนการคัดกรองคลินิกได้ที่ support@asd-project.org หรืออ่านในหน้าข้อมูลความปลอดภัย"
      );
    });
  }

  // ── Login button ──
  const loginBtn = document.getElementById('btn-login');
  if (loginBtn) {
    loginBtn.addEventListener('click', () => {
      alert(getCurrentLang() === 'en' ? 
        "Sign In feature is coming soon!" : 
        "ระบบเข้าสู่ระบบกำลังจะเปิดให้บริการเร็วๆ นี้!"
      );
    });
  }

  // ── Listen for external langchange events ──
  window.addEventListener('langchange', () => {
    refreshNavText();
  });
}

/**
 * Initialise AppShell layout widgets.
 */
export function initNav() {
  const container = document.getElementById('nav-container');
  if (container) {
    container.innerHTML = buildNavHTML();
  }

  // Prepend Top Bar dynamically inside main content area
  const mainContent = document.querySelector('.app-main');
  if (mainContent && !mainContent.querySelector('.top-bar')) {
    const topBar = document.createElement('header');
    topBar.className = 'top-bar';
    topBar.innerHTML = buildTopBarHTML();
    mainContent.insertBefore(topBar, mainContent.firstChild);
  }

  // Apply saved theme state
  initTheme();

  bindNavEvents();
}
