(function () {
  if (typeof L === 'undefined') return;

  document.querySelectorAll('.club-map').forEach(element => {
    const data = JSON.parse(element.dataset.map);
    const map = L.map(element, {
      dragging: false,
      scrollWheelZoom: false,
      zoomControl: false
    }).setView([data.lat, data.lng], 14);

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
    L.marker([data.lat, data.lng]).addTo(map).bindPopup(data.label);
  });
})();
