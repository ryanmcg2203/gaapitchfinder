(function () {
  const script = document.currentScript;
  if (!script) return;

  const input = document.getElementById(script.dataset.inputId || '');
  const empty = document.getElementById(script.dataset.emptyId || '');
  const itemSelector = script.dataset.itemSelector;
  if (!input || !itemSelector) return;

  const items = Array.from(document.querySelectorAll(itemSelector));

  function applyFilter() {
    const query = input.value.trim().toLowerCase();
    let visible = 0;
    items.forEach(item => {
      const text = (item.dataset.search || item.textContent || '').toLowerCase();
      const match = !query || text.includes(query);
      item.hidden = !match;
      if (match) visible += 1;
    });
    if (empty) empty.hidden = visible !== 0;
  }

  input.addEventListener('input', applyFilter);
  applyFilter();
})();
