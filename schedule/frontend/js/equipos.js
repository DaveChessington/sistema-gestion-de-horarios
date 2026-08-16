document.addEventListener('DOMContentLoaded', () => {
  const mockData = window.ScheduleMockData;
  const searchInput = document.getElementById('equipmentSearch');
  const plantelFilter = document.getElementById('equipmentPlantelFilter');
  const salonFilter = document.getElementById('equipmentSalonFilter');
  const statusFilter = document.getElementById('equipmentStatusFilter');
  const tableBody = document.getElementById('equipmentTableBody');
  const mobileGrid = document.getElementById('equipmentMobileGrid');
  const resultCount = document.getElementById('equipmentResultCount');
  const previousButton = document.getElementById('equipmentPreviousPage');
  const nextButton = document.getElementById('equipmentNextPage');
  const currentPageButton = document.getElementById('equipmentCurrentPage');

  if (!mockData || !tableBody || !mobileGrid) return;

  const planteles = mockData.readPlanteles();
  const salones = mockData.readSalones();
  const programas = mockData.readProgramas();
  const plantelChoices = [null, ...planteles.map((plantel) => Number(plantel.id))];
  const states = ['all', 'active', 'inactive'];
  const pageSize = 3;
  let selectedPlantelIndex = 0;
  let selectedSalonIndex = 0;
  let selectedState = 'all';
  let currentPage = 1;

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const salonFor = (equipo) => salones.find((salon) => Number(salon.id) === Number(equipo.idSalon));
  const plantelFor = (salon) => planteles.find((plantel) => Number(plantel.id) === Number(salon?.idPlantel));
  const programFor = (id) => programas.find((programa) => Number(programa.id) === Number(id));
  const salonChoices = () => {
    const selectedPlantel = plantelChoices[selectedPlantelIndex];
    const available = selectedPlantel === null
      ? salones
      : salones.filter((salon) => Number(salon.idPlantel) === selectedPlantel);
    return [null, ...available.map((salon) => Number(salon.id))];
  };

  const filteredEquipos = () => {
    const query = searchInput?.value.trim().toLocaleLowerCase('es') || '';
    const selectedPlantel = plantelChoices[selectedPlantelIndex];
    const selectedSalon = salonChoices()[selectedSalonIndex];

    return mockData.readEquipos().filter((equipo) => {
      const salon = salonFor(equipo);
      const plantel = plantelFor(salon);
      const searchable = `${equipo.numero} ${equipo.descripcion} ${salon?.numero || ''} ${plantel?.nombre || ''}`.toLocaleLowerCase('es');
      const matchesPlantel = selectedPlantel === null || Number(plantel?.id) === selectedPlantel;
      const matchesSalon = selectedSalon === null || Number(salon?.id) === selectedSalon;
      const matchesState = selectedState === 'all'
        || (selectedState === 'active' && equipo.activo)
        || (selectedState === 'inactive' && !equipo.activo);
      return searchable.includes(query) && matchesPlantel && matchesSalon && matchesState;
    });
  };

  const softwareTags = (equipo, compact = false) => {
    const associated = (Array.isArray(equipo.programas) ? equipo.programas : [])
      .map(programFor)
      .filter(Boolean);
    if (!associated.length) return '<span class="text-xs text-slate-400">Sin programas asociados</span>';
    const limit = compact ? 1 : 2;
    const visible = associated.slice(0, limit).map((programa) => `<span class="software-tag">${escapeHtml(programa.nombre)}</span>`);
    if (associated.length > limit) visible.push(`<span class="software-tag software-tag-more">+${associated.length - limit}</span>`);
    return visible.join('');
  };

  const tableRow = (equipo) => {
    const salon = salonFor(equipo);
    const plantel = plantelFor(salon);
    return `
      <tr class="catalog-row">
        <td class="px-6 py-4"><div class="flex items-center gap-3"><span class="flex h-10 w-10 items-center justify-center rounded-xl ${equipo.activo ? 'bg-violet-50 text-violet-600' : 'bg-slate-100 text-slate-500'}"><i class="fa-solid fa-computer"></i></span><div><p class="text-sm font-semibold">${escapeHtml(equipo.numero)}</p><p class="mt-1 text-xs text-slate-400">${escapeHtml(equipo.descripcion || 'Sin descripción')}</p></div></div></td>
        <td class="px-6 py-4"><p class="text-sm font-medium text-slate-700">${escapeHtml(salon?.numero || 'Sin salón asignado')}</p><p class="mt-1 text-xs text-slate-400">${escapeHtml(plantel?.nombre || 'Sin plantel')}</p></td>
        <td class="px-6 py-4"><div class="flex flex-wrap gap-1">${softwareTags(equipo)}</div></td>
        <td class="px-6 py-4"><span class="status-badge ${equipo.activo ? 'status-active' : 'status-inactive'}"><span></span>${equipo.activo ? 'Activo' : 'Inactivo'}</span></td>
        <td class="px-6 py-4"><div class="flex justify-end gap-2"><button type="button" aria-disabled="true" class="table-action" aria-label="Ver"><i class="fa-regular fa-eye"></i></button><button type="button" aria-disabled="true" class="table-action" aria-label="Editar"><i class="fa-regular fa-pen-to-square"></i></button><button type="button" aria-disabled="true" class="table-action table-action-danger" aria-label="Eliminar"><i class="fa-regular fa-trash-can"></i></button></div></td>
      </tr>`;
  };

  const mobileCard = (equipo) => {
    const salon = salonFor(equipo);
    const plantel = plantelFor(salon);
    return `
      <article class="resource-card">
        <div class="flex items-start justify-between"><div class="flex items-center gap-3"><span class="resource-icon ${equipo.activo ? 'bg-violet-50 text-violet-600' : 'bg-slate-100 text-slate-500'}"><i class="fa-solid fa-computer"></i></span><div><h3 class="font-semibold">${escapeHtml(equipo.numero)}</h3><p class="mt-1 text-xs text-slate-400">${escapeHtml(salon?.numero || 'Sin salón asignado')}</p></div></div><span class="status-badge ${equipo.activo ? 'status-active' : 'status-inactive'}"><span></span>${equipo.activo ? 'Activo' : 'Inactivo'}</span></div>
        <p class="mt-4 text-xs text-slate-500">${escapeHtml(plantel?.nombre || 'Sin plantel')}</p><div class="mt-3 flex flex-wrap gap-1">${softwareTags(equipo, true)}</div>
      </article>`;
  };

  const render = () => {
    const equipos = filteredEquipos();
    const pages = Math.max(1, Math.ceil(equipos.length / pageSize));
    currentPage = Math.min(currentPage, pages);
    const visible = equipos.slice((currentPage - 1) * pageSize, currentPage * pageSize);
    const selectedPlantel = plantelChoices[selectedPlantelIndex];
    const currentSalonChoices = salonChoices();
    selectedSalonIndex = Math.min(selectedSalonIndex, currentSalonChoices.length - 1);
    const selectedSalon = currentSalonChoices[selectedSalonIndex];

    tableBody.innerHTML = visible.length
      ? visible.map(tableRow).join('')
      : '<tr><td colspan="5" class="px-6 py-12 text-center text-sm text-slate-400">No se encontraron equipos.</td></tr>';
    mobileGrid.innerHTML = visible.length
      ? visible.map(mobileCard).join('')
      : '<p class="py-10 text-center text-sm text-slate-400">No se encontraron equipos.</p>';
    if (resultCount) resultCount.innerHTML = `Mostrando <strong class="text-slate-700">${visible.length} de ${equipos.length}</strong> equipos`;
    if (currentPageButton) currentPageButton.textContent = String(currentPage);
    if (previousButton) previousButton.disabled = currentPage <= 1;
    if (nextButton) nextButton.disabled = currentPage >= pages;

    const plantelLabel = plantelFilter?.querySelector('[data-filter-label]');
    const salonLabel = salonFilter?.querySelector('[data-filter-label]');
    const statusLabel = statusFilter?.querySelector('[data-filter-label]');
    if (plantelLabel) plantelLabel.textContent = selectedPlantel === null ? 'Plantel: todos' : planteles.find((plantel) => Number(plantel.id) === selectedPlantel)?.nombre || 'Plantel';
    if (salonLabel) salonLabel.textContent = selectedSalon === null ? 'Salón: todos' : salones.find((salon) => Number(salon.id) === selectedSalon)?.numero || 'Salón';
    if (statusLabel) statusLabel.textContent = selectedState === 'all' ? 'Estado: todos' : selectedState === 'active' ? 'Activos' : 'Inactivos';
  };

  searchInput?.addEventListener('input', () => { currentPage = 1; render(); });
  plantelFilter?.addEventListener('click', () => { selectedPlantelIndex = (selectedPlantelIndex + 1) % plantelChoices.length; selectedSalonIndex = 0; currentPage = 1; render(); });
  salonFilter?.addEventListener('click', () => { const choices = salonChoices(); selectedSalonIndex = (selectedSalonIndex + 1) % choices.length; currentPage = 1; render(); });
  statusFilter?.addEventListener('click', () => { selectedState = states[(states.indexOf(selectedState) + 1) % states.length]; currentPage = 1; render(); });
  previousButton?.addEventListener('click', () => { currentPage -= 1; render(); });
  nextButton?.addEventListener('click', () => { currentPage += 1; render(); });

  render();
});
