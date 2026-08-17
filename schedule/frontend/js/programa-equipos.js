document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('programEquipmentSearch');
  const filterButton = document.getElementById('programEquipmentFilter');
  const filterLabel = filterButton?.querySelector('[data-filter-label]');
  const cards = Array.from(document.querySelectorAll('[data-program-equipment-card]'));
  const emptyState = document.getElementById('programEquipmentEmpty');
  const resultCount = document.getElementById('programEquipmentResultCount');
  const filters = ['all', 'associated', 'available'];
  let selectedFilter = 'all';

  const render = () => {
    const query = searchInput?.value.trim().toLocaleLowerCase('es') || '';
    let visibleCount = 0;
    cards.forEach((card) => {
      const associated = card.dataset.associated === 'true';
      const matchesSearch = (card.dataset.search || '').toLocaleLowerCase('es').includes(query);
      const matchesFilter = selectedFilter === 'all'
        || (selectedFilter === 'associated' && associated)
        || (selectedFilter === 'available' && !associated);
      const visible = matchesSearch && matchesFilter;
      card.classList.toggle('hidden', !visible);
      if (visible) visibleCount += 1;
    });

    emptyState?.classList.toggle('hidden', visibleCount > 0);
    if (resultCount) resultCount.innerHTML = `Mostrando <strong class="text-slate-700">${visibleCount} de ${cards.length}</strong> equipos`;
    if (filterLabel) {
      filterLabel.textContent = selectedFilter === 'all'
        ? 'Asociación: todas'
        : selectedFilter === 'associated' ? 'Vinculados' : 'Disponibles';
    }
  };

  searchInput?.addEventListener('input', render);
  filterButton?.addEventListener('click', () => {
    selectedFilter = filters[(filters.indexOf(selectedFilter) + 1) % filters.length];
    render();
  });
  document.addEventListener('submit', (event) => {
    const removeForm = event.target.closest('[data-program-equipment-remove]');
    if (!removeForm) return;
    const label = removeForm.dataset.equipmentLabel || 'este equipo';
    if (!window.confirm(`¿Desvincular el programa de ${label}?`)) event.preventDefault();
  });

  render();
});
