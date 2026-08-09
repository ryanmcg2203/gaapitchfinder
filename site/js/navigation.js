(function () {
  const toggle = document.getElementById('hamburger');
  const drawer = document.getElementById('nav-drawer');
  const closeButton = document.getElementById('drawer-close');
  if (!toggle || !drawer || !closeButton) return;

  toggle.setAttribute('aria-controls', drawer.id);

  function setOpen(open, returnFocus = false) {
    drawer.classList.toggle('open', open);
    drawer.toggleAttribute('inert', !open);
    drawer.setAttribute('aria-hidden', String(!open));
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    if (open) {
      closeButton.focus();
    } else if (returnFocus) {
      toggle.focus();
    }
  }

  setOpen(false);
  toggle.addEventListener('click', () => setOpen(!drawer.classList.contains('open')));
  closeButton.addEventListener('click', () => setOpen(false, true));
  drawer.addEventListener('click', event => {
    if (event.target.closest('a')) setOpen(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && drawer.classList.contains('open')) {
      event.preventDefault();
      setOpen(false, true);
    }
  });
})();
