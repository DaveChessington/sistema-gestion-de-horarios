document.addEventListener('DOMContentLoaded', () => {
  const mockData = window.ScheduleMockData;
  const searchInput = document.getElementById('salonSearch');
  const plantelFilter = document.getElementById('salonPlantelFilter');
  const plantelFilterLabel = plantelFilter?.querySelector('[data-filter-label]');
  const statusFilter = document.getElementById('salonStatusFilter');
  const statusFilterLabel = statusFilter?.querySelector('[data-filter-label]');
  const cardGrid = document.getElementById('salonCardGrid');
  const resultCount = document.getElementById('salonResultCount');
  const previousButton = document.getElementById('salonPreviousPage');
  const nextButton = document.getElementById('salonNextPage');
  const currentPageButton = document.getElementById('salonCurrentPage');

  if (!mockData || !cardGrid) return;

  const pageSize = 3;
  const states = ['all', 'active', 'inactive'];
  const planteles = mockData.readPlanteles();
  const plantelChoices = [null, ...planteles.map((plantel) => Number(plantel.id))];
  let selectedPlantelIndex = 0;
  let selectedState = 'all';
  let currentPage = 1;

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const plantelName = (id) => planteles.find((plantel) => Number(plantel.id) === Number(id))?.nombre || 'Sin plantel';

  const filteredSalones = () => {
    const query = searchInput?.value.trim().toLocaleLowerCase('es') || '';
    const selectedPlantel = plantelChoices[selectedPlantelIndex];
    return mockData.readSalones().filter((salon) => {
      const matchesQuery = `${salon.numero} ${salon.descripcion}`.toLocaleLowerCase('es').includes(query);
      const matchesPlantel = selectedPlantel === null || Number(salon.idPlantel) === selectedPlantel;
      const matchesState = selectedState === 'all'
        || (selectedState === 'active' && salon.activo)
        || (selectedState === 'inactive' && !salon.activo);
      return matchesQuery && matchesPlantel && matchesState;
    });
  };

  const salonCard = (salon) => `
    <article class="resource-card">
      <div class="flex items-start justify-between"><span class="resource-icon ${salon.activo ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'}"><i class="fa-solid ${salon.activo ? 'fa-door-open' : 'fa-screwdriver-wrench'}"></i></span><span class="status-badge ${salon.activo ? 'status-active' : 'status-maintenance'}"><span></span>${salon.activo ? 'Activo' : 'Mantenimiento'}</span></div>
      <h3 class="mt-5 text-lg font-semibold">${escapeHtml(salon.numero)}</h3><p class="mt-1 text-sm text-slate-500">${escapeHtml(salon.descripcion || 'Sin descripción')}</p>
      <div class="mt-5 grid grid-cols-2 gap-3 border-y border-slate-100 py-4"><div><p class="resource-label">Plantel</p><p class="resource-value">${escapeHtml(plantelName(salon.idPlantel))}</p></div><div><p class="resource-label">Capacidad</p><p class="resource-value">${Number(salon.capacidad)} personas</p></div></div>
      <div class="mt-4 flex items-center justify-between"><span class="text-xs text-slate-400">ID ${salon.id}</span><div class="flex gap-2"><button type="button" aria-disabled="true" class="table-action" aria-label="Ver"><i class="fa-regular fa-eye"></i></button><button type="button" aria-disabled="true" class="table-action" aria-label="Editar"><i class="fa-regular fa-pen-to-square"></i></button></div></div>
    </article>`;

  const render = () => {
    const salones = filteredSalones();
    const pageCount = Math.max(1, Math.ceil(salones.length / pageSize));
    currentPage = Math.min(currentPage, pageCount);
    const visible = salones.slice((currentPage - 1) * pageSize, currentPage * pageSize);
    const selectedPlantel = plantelChoices[selectedPlantelIndex];

    cardGrid.innerHTML = visible.length
      ? visible.map(salonCard).join('')
      : '<p class="col-span-full py-12 text-center text-sm text-slate-400">No se encontraron salones.</p>';
    if (resultCount) resultCount.innerHTML = `Mostrando <strong class="text-slate-700">${visible.length} de ${salones.length}</strong> salones`;
    if (currentPageButton) currentPageButton.textContent = String(currentPage);
    if (previousButton) previousButton.disabled = currentPage <= 1;
    if (nextButton) nextButton.disabled = currentPage >= pageCount;
    if (plantelFilterLabel) plantelFilterLabel.textContent = selectedPlantel === null ? 'Plantel: todos' : plantelName(selectedPlantel);
    if (statusFilterLabel) statusFilterLabel.textContent = selectedState === 'all' ? 'Estado: todos' : selectedState === 'active' ? 'Activos' : 'Mantenimiento';

    const visibleCount = document.getElementById('salonVisibleCount');
    const capacityTotal = document.getElementById('salonCapacityTotal');
    const inactiveCount = document.getElementById('salonInactiveCount');
    if (visibleCount) visibleCount.textContent = String(salones.length);
    if (capacityTotal) capacityTotal.textContent = String(salones.reduce((total, salon) => total + Number(salon.capacidad || 0), 0));
    if (inactiveCount) inactiveCount.textContent = String(salones.filter((salon) => !salon.activo).length);
  };

  searchInput?.addEventListener('input', () => { currentPage = 1; render(); });
  plantelFilter?.addEventListener('click', () => { selectedPlantelIndex = (selectedPlantelIndex + 1) % plantelChoices.length; currentPage = 1; render(); });
  statusFilter?.addEventListener('click', () => { selectedState = states[(states.indexOf(selectedState) + 1) % states.length]; currentPage = 1; render(); });
  previousButton?.addEventListener('click', () => { currentPage -= 1; render(); });
  nextButton?.addEventListener('click', () => { currentPage += 1; render(); });

  render();
});
