/**
 * nav.js — Shared Navigation & AppShell Component (Redesigned)
 *
 * Injects a modern desktop top horizontal navigation, mobile top bar,
 * mobile drawer menu, and mobile bottom tab navigation.
 * Handles theme toggling, language switching, help dialogs, and mobile drawers.
 */

import { getCurrentLang, setLang, t } from './i18n.js';
import { initResults } from './results-display.js';
import { initEducation } from './education.js';

// ─── Header Navigation Links ────────────────────────────────────────────────
const NAV_LINKS = [
  { key: 'home',      href: '#home',      i18n: 'nav.home' },
  { key: 'screening', href: '#screening',   i18n: 'nav.screening' },
  { key: 'results',   href: '#results',     i18n: 'nav.results' },
  { key: 'education', href: '#education',   i18n: 'nav.education' },
  { key: 'about',     href: '#about',       i18n: 'nav.about' },
  { key: 'resources', href: '#resources',   i18n: 'nav.resources' },
];

// ─── Mobile Bottom Tabs ─────────────────────────────────────────────────────
const BOTTOM_TABS = [
  { key: 'home',      href: '#home',      i18n: 'nav.home',      icon: '🏠' },
  { key: 'screening', href: '#screening',   i18n: 'nav.screening', icon: '📋' },
  { key: 'results',   href: '#results',     i18n: 'nav.results',   icon: '📊' },
  { key: 'education', href: '#education',   i18n: 'nav.education', icon: '📖' },
  { key: 'profile',   href: '#profile',     i18n: 'nav.profile',   icon: '👤' },
];

/**
 * Determine which page key is currently active based on pathname.
 */
function getActivePage() {
  const hash = window.location.hash || '#home';
  const key = hash.substring(1);
  if (['home', 'screening', 'results', 'education', 'about', 'resources', 'profile', 'settings'].includes(key)) {
    return key;
  }
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
 * Build navigation HTML dynamically.
 */
function buildNavHTML() {
  const activePage = getActivePage();
  const lang = getCurrentLang();
  const toggleLabel = lang === 'en' ? '🌐 TH' : '🌐 EN';

  // Desktop Header Links
  const desktopLinks = NAV_LINKS.map(({ key, href, i18n }) => {
    const activeClass = key === activePage ? ' active' : '';
    return `<a href="${href}" class="nav-item-link${activeClass}" data-i18n="${i18n}">${t(i18n)}</a>`;
  }).join('');

  // Mobile Drawer Links
  const drawerLinks = NAV_LINKS.map(({ key, href, i18n }) => {
    const activeClass = key === activePage ? ' active' : '';
    return `<a href="${href}" class="sidebar-link drawer-link${activeClass}" data-i18n="${i18n}">${t(i18n)}</a>`;
  }).join('');

  // Mobile Bottom Tabs Links
  const bottomTabs = BOTTOM_TABS.map(({ key, href, i18n, icon }) => {
    const activeClass = key === activePage ? ' active' : '';
    return `
      <a href="${href}" class="bottom-tab-item${activeClass}" data-i18n="${i18n}">
        <span class="tab-icon">${icon}</span>
        <span class="tab-text">${t(i18n)}</span>
      </a>
    `;
  }).join('');

  return `
    <!-- Desktop Header -->
    <header class="desktop-header hide-mobile">
      <div class="header-container">
        <a href="index.html" class="header-logo">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" width="24" height="24">
              <path fill="currentColor" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
              <path d="M12 7V13M9 10H15" stroke="white" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="logo-text">
            <span class="logo-title">ASD Screening</span>
            <span class="logo-subtitle">คัดกรองออทิซึมในเด็ก</span>
          </div>
        </a>
        <nav class="header-nav">
          ${desktopLinks}
        </nav>
        <div class="header-actions">
          <button class="top-bar-btn" id="btn-theme-toggle" title="Toggle Theme" aria-label="Toggle Theme">🌓</button>
          <button class="top-bar-btn" id="btn-help" title="${t('nav.help') || 'Help'}">❓</button>
          <button class="lang-toggle header-lang-btn" data-lang-toggle aria-label="Switch language">
            ${toggleLabel}
          </button>
          <a href="profile.html" class="btn btn-primary login-btn" id="btn-login">
            <span class="login-icon">👤</span>
            <span class="login-text" data-i18n="nav.login">${t('nav.login')}</span>
          </a>
        </div>
      </div>
    </header>

    <!-- Mobile Header -->
    <header class="mobile-header hide-desktop">
      <a href="index.html" class="mobile-logo-group">
        <div class="mobile-logo-icon">
          <svg viewBox="0 0 24 24" width="20" height="20">
            <path fill="currentColor" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
            <path d="M12 7V13M9 10H15" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="mobile-logo-text">
          <span class="mobile-logo-title">ASD Screening</span>
          <span class="mobile-logo-subtitle">คัดกรองออทิซึมในเด็ก</span>
        </div>
      </a>
      <button class="nav-toggle" aria-label="Toggle menu" aria-expanded="false">
        <span></span>
        <span></span>
        <span></span>
      </button>
    </header>

    <!-- Mobile Drawer Sidebar -->
    <aside class="sidebar mobile-drawer hide-desktop" role="navigation" aria-label="Main navigation">
      <div class="mobile-drawer-brand">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" width="24" height="24">
            <path fill="currentColor" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
            <path d="M12 7V13M9 10H15" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="mobile-drawer-logo-text">
          <span class="logo-title">ASD Screening</span>
          <span class="logo-subtitle">คัดกรองออทิซึมในเด็ก</span>
        </div>
      </div>
      <nav class="sidebar-menu">
        ${drawerLinks}
      </nav>
      <div class="sidebar-footer">
        <button class="top-bar-btn" id="btn-drawer-theme-toggle" style="width: auto; padding: 6px 12px; font-size: var(--text-xs);" title="Toggle Theme">🌓 ธีม</button>
        <button class="lang-toggle" data-lang-toggle aria-label="Switch language">
          ${toggleLabel}
        </button>
      </div>
    </aside>

    <!-- Mobile Bottom Navigation -->
    <nav class="mobile-bottom-nav hide-desktop">
      ${bottomTabs}
    </nav>
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

  // Update Desktop Header Links and Drawer Links
  NAV_LINKS.forEach(({ href, i18n }) => {
    document.querySelectorAll(`.desktop-header a[href="${href}"]`).forEach(link => {
      link.textContent = t(i18n);
    });
    document.querySelectorAll(`.mobile-drawer a[href="${href}"]`).forEach(link => {
      link.textContent = t(i18n);
    });
  });

  // Update Mobile Bottom Tabs
  BOTTOM_TABS.forEach(({ href, i18n, icon }) => {
    document.querySelectorAll(`.mobile-bottom-nav a[href="${href}"]`).forEach(link => {
      link.innerHTML = `
        <span class="tab-icon">${icon}</span>
        <span class="tab-text">${t(i18n)}</span>
      `;
    });
  });

  // Update all lang toggle buttons (header and drawer)
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
  const sidebar = container.querySelector('.sidebar.mobile-drawer');

  if (hamburger && sidebar) {
    hamburger.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = sidebar.classList.toggle('open');
      hamburger.classList.toggle('active', isOpen);
      hamburger.setAttribute('aria-expanded', String(isOpen));
    });

    sidebar.querySelectorAll('.drawer-link').forEach((link) => {
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

  // ── Theme toggle (Desktop) ──
  const themeToggle = document.getElementById('btn-theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const isDark = document.body.classList.toggle('dark');
      localStorage.setItem('asd-theme', isDark ? 'dark' : 'light');
    });
  }

  // ── Theme toggle (Mobile Drawer) ──
  const drawerThemeToggle = document.getElementById('btn-drawer-theme-toggle');
  if (drawerThemeToggle) {
    drawerThemeToggle.addEventListener('click', () => {
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
    loginBtn.addEventListener('click', (e) => {
      // Don't block clicking if it behaves as a normal link to profile.html
      // but alert if needed or do redirect
    });
  }

  // ── Listen for external langchange events ──
  window.addEventListener('langchange', () => {
    refreshNavText();
  });
}

/**
 * Switch view section and update active nav indicators based on hash routing.
 */
export function handleHashRouting() {
  const activePage = getActivePage();
  const hash = `#${activePage}`;

  // Hide all view sections
  document.querySelectorAll('.view-section').forEach((section) => {
    section.style.display = 'none';
  });

  // Show active view section
  const activeSection = document.getElementById(`view-${activePage}`);
  if (activeSection) {
    activeSection.style.display = '';
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  // Update classes in Desktop Header
  document.querySelectorAll('.desktop-header .nav-item-link').forEach((link) => {
    const href = link.getAttribute('href');
    if (href === hash) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  // Update classes in Mobile Bottom Nav
  document.querySelectorAll('.mobile-bottom-nav .bottom-tab-item').forEach((link) => {
    const href = link.getAttribute('href');
    if (href === hash) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  // Update classes in Mobile Drawer Menu
  document.querySelectorAll('.sidebar.mobile-drawer .sidebar-link').forEach((link) => {
    const href = link.getAttribute('href');
    if (href === hash) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  // Specific page hooks
  if (activePage === 'results') {
    initResults();
  } else if (activePage === 'education') {
    initEducation();
  }
}

/**
 * Initialise AppShell layout widgets.
 */
export function initNav() {
  const container = document.getElementById('nav-container');
  if (container) {
    container.innerHTML = buildNavHTML();
  }

  // Apply saved theme state
  initTheme();

  bindNavEvents();

  // Listen to hash changes for SPA routing
  window.addEventListener('hashchange', handleHashRouting);

  // Initial routing check
  handleHashRouting();
}
