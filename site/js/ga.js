(function () {
  'use strict';

  const MEASUREMENT_ID = 'G-8R6YMPVNWH';
  const CONSENT_KEY = 'gaa-analytics-consent';
  const CONSENT_MAX_AGE_MS = 180 * 24 * 60 * 60 * 1000;
  const SCRIPT_ID = 'gaa-google-analytics';
  const DIALOG_ID = 'analytics-consent-dialog';
  const VALID_CHOICES = new Set(['accepted', 'rejected']);
  const disableKey = `ga-disable-${MEASUREMENT_ID}`;
  let currentChoice = readConsent();
  let dialog;
  let closeButton;
  let statusText;
  let preferencesTrigger;
  let returnFocusOnClose = false;

  window[disableKey] = currentChoice !== 'accepted';

  function readConsent() {
    try {
      const saved = JSON.parse(window.localStorage.getItem(CONSENT_KEY));
      const decidedAt = Number(saved && saved.decidedAt);
      if (
        !saved ||
        !VALID_CHOICES.has(saved.choice) ||
        !Number.isFinite(decidedAt) ||
        decidedAt > Date.now() ||
        Date.now() - decidedAt > CONSENT_MAX_AGE_MS
      ) {
        window.localStorage.removeItem(CONSENT_KEY);
        return null;
      }
      return saved.choice;
    } catch (_error) {
      return null;
    }
  }

  function saveConsent(choice) {
    try {
      window.localStorage.setItem(
        CONSENT_KEY,
        JSON.stringify({ choice, decidedAt: Date.now() })
      );
    } catch (_error) {
      // The choice still applies to this page when browser storage is unavailable.
    }
  }

  function expireCookie(name, domain) {
    const domainPart = domain ? `; domain=${domain}` : '';
    document.cookie = `${name}=; Max-Age=0; path=/${domainPart}; SameSite=Lax`;
  }

  function clearAnalyticsCookies() {
    const cookieNames = document.cookie
      .split(';')
      .map(cookie => cookie.split('=')[0].trim())
      .filter(name => name === '_ga' || name.startsWith('_ga_'));
    const hostname = window.location.hostname;
    const domains = hostname && hostname !== 'localhost'
      ? ['', hostname, `.${hostname}`]
      : [''];
    cookieNames.forEach(name => {
      domains.forEach(domain => expireCookie(name, domain));
    });
  }

  function stopAnalytics() {
    window[disableKey] = true;
    document.getElementById(SCRIPT_ID)?.remove();
    clearAnalyticsCookies();
  }

  function loadAnalytics() {
    if (currentChoice !== 'accepted' || document.getElementById(SCRIPT_ID)) return;

    window[disableKey] = false;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () {
      window.dataLayer.push(arguments);
    };
    window.gtag('js', new Date());
    window.gtag('config', MEASUREMENT_ID);

    const script = document.createElement('script');
    script.id = SCRIPT_ID;
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(MEASUREMENT_ID)}`;
    script.addEventListener('error', () => script.remove(), { once: true });
    document.head.appendChild(script);
  }

  function choiceStatus() {
    if (currentChoice === 'accepted') return 'Current choice: optional analytics is enabled.';
    if (currentChoice === 'rejected') return 'Current choice: optional analytics is disabled.';
    return 'Analytics is off until you choose.';
  }

  function updateDialog() {
    if (!dialog) return;
    statusText.textContent = choiceStatus();
    closeButton.hidden = !currentChoice;
    dialog.querySelectorAll('[data-analytics-choice]').forEach(button => {
      const selected = button.dataset.analyticsChoice === currentChoice;
      button.setAttribute('aria-pressed', String(selected));
    });
  }

  function closeDialog() {
    if (!dialog || dialog.hidden) return;
    dialog.hidden = true;
    preferencesTrigger?.setAttribute('aria-expanded', 'false');
    if (returnFocusOnClose) preferencesTrigger?.focus();
    returnFocusOnClose = false;
  }

  function openDialog(fromTrigger = false) {
    if (!dialog) return;
    returnFocusOnClose = fromTrigger;
    updateDialog();
    dialog.hidden = false;
    preferencesTrigger?.setAttribute('aria-expanded', 'true');
    if (fromTrigger) {
      const focusTarget = closeButton.hidden
        ? dialog.querySelector('[data-analytics-choice="rejected"]')
        : closeButton;
      focusTarget?.focus();
    }
  }

  function applyChoice(choice) {
    if (!VALID_CHOICES.has(choice)) return;
    currentChoice = choice;
    saveConsent(choice);
    if (choice === 'accepted') loadAnalytics();
    else stopAnalytics();
    updateDialog();
    closeDialog();
    window.dispatchEvent(
      new CustomEvent('gaa:analytics-consent-changed', { detail: { choice } })
    );
  }

  function createPreferencesTrigger() {
    const nav = document.querySelector('.site-nav');
    if (!nav) return;
    preferencesTrigger = document.createElement('button');
    preferencesTrigger.type = 'button';
    preferencesTrigger.className = 'analytics-preferences-trigger';
    preferencesTrigger.setAttribute('aria-label', 'Analytics preferences');
    preferencesTrigger.setAttribute('aria-controls', DIALOG_ID);
    preferencesTrigger.setAttribute('aria-expanded', 'false');
    preferencesTrigger.title = 'Analytics preferences';
    preferencesTrigger.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h10M18 7h2M4 17h2M10 17h10M14 4v6M6 14v6"/></svg>';
    const menuButton = nav.querySelector('.nav-hamburger');
    nav.insertBefore(preferencesTrigger, menuButton || null);
    preferencesTrigger.addEventListener('click', () => openDialog(true));
  }

  function createDialog() {
    dialog = document.createElement('section');
    dialog.id = DIALOG_ID;
    dialog.className = 'analytics-consent';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-labelledby', 'analytics-consent-title');
    dialog.setAttribute('aria-describedby', 'analytics-consent-description analytics-consent-status');
    dialog.hidden = true;
    dialog.innerHTML = `
      <button class="analytics-consent-close" type="button" aria-label="Close analytics preferences">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>
      </button>
      <h2 id="analytics-consent-title">Optional analytics</h2>
      <p id="analytics-consent-description">Google Analytics helps us understand broad site usage. It stays off unless you accept. <a href="/privacy.html#analytics">Privacy details</a></p>
      <p class="analytics-consent-status" id="analytics-consent-status" aria-live="polite"></p>
      <div class="analytics-consent-actions">
        <button type="button" data-analytics-choice="rejected">Reject analytics</button>
        <button type="button" data-analytics-choice="accepted">Accept analytics</button>
      </div>
    `;
    document.body.appendChild(dialog);
    closeButton = dialog.querySelector('.analytics-consent-close');
    statusText = dialog.querySelector('.analytics-consent-status');
    closeButton.addEventListener('click', closeDialog);
    dialog.addEventListener('click', event => {
      const choiceButton = event.target.closest('[data-analytics-choice]');
      if (choiceButton) applyChoice(choiceButton.dataset.analyticsChoice);
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && currentChoice && !dialog.hidden) {
        event.preventDefault();
        closeDialog();
      }
    });
  }

  function init() {
    createPreferencesTrigger();
    createDialog();
    updateDialog();
    if (currentChoice === 'accepted') loadAnalytics();
    else if (!currentChoice) openDialog();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
