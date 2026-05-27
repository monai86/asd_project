/**
 * education.js — Education Page Behavior
 *
 * Sets up accordion sections (native <details>/<summary>),
 * smooth open/close transitions, scroll-reveal animations
 * via IntersectionObserver, and bilingual content.
 */

import { initI18n, applyTranslations, t, getCurrentLang } from './i18n.js';
import { initNav } from './nav.js';

// ─── Accordion smooth transitions ───────────────────────────────────────────

/**
 * Enhance all <details> elements with smooth height-transition animations.
 * Uses the Web Animations API for clean open/close effects.
 */
function enhanceAccordions() {
  const allDetails = document.querySelectorAll('.edu-section details');

  allDetails.forEach((details) => {
    const summary = details.querySelector('summary');
    const content = details.querySelector('.details-content');
    if (!summary || !content) return;

    // Prevent default toggle so we can animate
    summary.addEventListener('click', (e) => {
      e.preventDefault();

      if (details.open) {
        // ── Closing animation ──
        const startHeight = `${details.offsetHeight}px`;
        const endHeight   = `${summary.offsetHeight}px`;

        const anim = details.animate(
          { height: [startHeight, endHeight] },
          { duration: 300, easing: 'ease-in-out' }
        );

        anim.onfinish = () => {
          details.open = false;
          details.style.height = '';
          details.style.overflow = '';
        };

        details.style.overflow = 'hidden';
      } else {
        // ── Opening animation ──
        details.open = true;

        const startHeight = `${summary.offsetHeight}px`;
        const endHeight   = `${details.offsetHeight}px`;

        const anim = details.animate(
          { height: [startHeight, endHeight] },
          { duration: 300, easing: 'ease-in-out' }
        );

        anim.onfinish = () => {
          details.style.height = '';
          details.style.overflow = '';
        };

        details.style.overflow = 'hidden';
      }
    });
  });
}


// ─── Scroll-reveal via IntersectionObserver ──────────────────────────────────

/**
 * Fade-and-slide sections into view as the user scrolls down.
 */
function initScrollReveal() {
  const sections = document.querySelectorAll('.edu-section');

  if (!sections.length) return;

  // Add initial hidden state
  sections.forEach((section) => {
    section.classList.add('edu-section--hidden');
  });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('edu-section--visible');
          entry.target.classList.remove('edu-section--hidden');
          observer.unobserve(entry.target); // animate only once
        }
      });
    },
    {
      threshold: 0.15,
      rootMargin: '0px 0px -40px 0px',
    }
  );

  sections.forEach((section) => observer.observe(section));
}


// ─── Smooth in-page scrolling ───────────────────────────────────────────────

function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (e) => {
      const target = document.querySelector(link.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}


// ─── FAQ section builder ────────────────────────────────────────────────────

/**
 * Build the FAQ section from i18n strings, appending it to
 * the FAQ container if it doesn't already have content.
 */
function buildFAQ() {
  const container = document.getElementById('faq-container');
  if (!container || container.children.length > 0) return;

  const faqs = [
    { q: 'education.faq1Q', a: 'education.faq1A' },
    { q: 'education.faq2Q', a: 'education.faq2A' },
    { q: 'education.faq3Q', a: 'education.faq3A' },
    { q: 'education.faq4Q', a: 'education.faq4A' },
  ];

  faqs.forEach(({ q, a }) => {
    const details = document.createElement('details');
    details.className = 'faq-item';

    const summary = document.createElement('summary');
    summary.className = 'faq-question';
    summary.setAttribute('data-i18n', q);
    summary.textContent = t(q);

    const content = document.createElement('div');
    content.className = 'details-content faq-answer';

    const p = document.createElement('p');
    p.setAttribute('data-i18n', a);
    p.textContent = t(a);
    content.appendChild(p);

    details.appendChild(summary);
    details.appendChild(content);
    container.appendChild(details);
  });
}


// ─── Public API ─────────────────────────────────────────────────────────────

/**
 * Initialise the education page.
 * Call once inside DOMContentLoaded.
 */
export function initEducation() {
  // Core modules
  initI18n();
  initNav();

  // Build dynamic FAQ
  buildFAQ();

  // Apply translations to all data-i18n elements
  applyTranslations();

  // Enhance accordions
  enhanceAccordions();

  // Scroll animations
  initScrollReveal();

  // Smooth anchor scrolling
  initSmoothScroll();

  // Re-apply translations on language change
  window.addEventListener('langchange', () => {
    applyTranslations();
    // Rebuild FAQ with new language
    const container = document.getElementById('faq-container');
    if (container) {
      container.innerHTML = '';
      buildFAQ();
      enhanceAccordions();
    }
  });
}
