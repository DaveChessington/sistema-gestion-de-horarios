document.addEventListener('DOMContentLoaded', () => {
  const mockData = window.ScheduleMockData;
  const searchInput = document.getElementById('programSearch');
  const statusFilter = document.getElementById('programStatusFilter');
  const statusFilterLabel = statusFilter?.querySelector('[data-filter-label]');
  const cardGrid = document.getElementById('programCardGrid');
  const resultCount = document.getElementById('programResultCount');
  const previousButton = document.getElementById('programPreviousPage');
  const nextButton = document.getElementById('programNextPage');
  const currentPageButton = document.getElementById('programCurrentPage');

  if (!mockData || !cardGrid) return;

  const pageSize = 3;
  const states = ['all', 'active', 'inactive'];
  const allowedIcons = new Set(['fa-solid fa-code', 'fa-brands fa-python', 'fa-solid fa-database', 'fa-brands fa-docker', 'fa-brands fa-git-alt', 'fa-brands fa-node-js']);
  const allowedColors = new Set(['bg-blue-600', 'bg-sky-500', 'bg-indigo-600', 'bg-slate-800', 'bg-orange-600', 'bg-emerald-600']);
  let selectedState = 'all';
  let currentPage = 1;

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const filteredProgramas = () => {
    const query = searchInput?.value.trim().toLocaleLowerCase('es') || '';
    return mockData.readProgramas().filter((programa) => {
      const matchesQuery = `${programa.nombre} ${programa.descripcion}`.toLocaleLowerCase('es').includes(query);
      const matchesState = selectedState === 'all'
        || (selectedState === 'active' && programa.activo)
        || (selectedState === 'inactive' && !programa.activo);
      return matchesQuery && matchesState;
    });
  };

  const programCard = (programa) => {
    const associated = Number(programa.equiposAsociados) || 0;
    const icon = allowedIcons.has(programa.icono) ? programa.icono : 'fa-solid fa-box';
    const color = allowedColors.has(programa.color) ? programa.color : 'bg-amber-500';
    const associationText = associated === 0 ? 'Sin asignar' : `${associated} ${associated === 1 ? 'estación' : 'estaciones'}`;

    return `
      <article class="software-card">
        <div class="flex items-start justify-between"><span class="software-logo ${color} text-white"><i class="${icon}"></i></span><span class="status-badge ${programa.activo ? 'status-active' : 'status-inactive'}"><span></span>${programa.activo ? 'Activo' : 'Inactivo'}</span></div>
        <h3 class="mt-5 text-base font-semibold">${escapeHtml(programa.nombre)}</h3>
        <p class="mt-2 min-h-10 text-xs leading-5 text-slate-500">${escapeHtml(programa.descripcion || 'Sin descripción')}</p>
        <div class="mt-5 flex items-center justify-between border-t border-slate-100 pt-4"><div><p class="resource-label">Equipos asociados</p><p class="resource-value">${associationText}</p></div><div class="flex gap-2"><button type="button" aria-disabled="true" class="table-action" aria-label="Asociar equipos"><i class="fa-solid fa-link"></i></button><button type="button" aria-disabled="true" class="table-action" aria-label="Editar"><i class="fa-regular fa-pen-to-square"></i></button></div></div>
      </article>`;
  };

  const render = () => {
    const allProgramas = mockData.readProgramas();
    const programas = filteredProgramas();
    const pageCount = Math.max(1, Math.ceil(programas.length / pageSize));
    currentPage = Math.min(currentPage, pageCount);
    const visible = programas.slice((currentPage - 1) * pageSize, currentPage * pageSize);

    cardGrid.innerHTML = visible.length
      ? visible.map(programCard).join('')
      : '<p class="col-span-full py-12 text-center text-sm text-slate-400">No se encontraron programas.</p>';
    if (resultCount) resultCount.innerHTML = `Mostrando <strong class="text-slate-700">${visible.length} de ${programas.length}</strong> programas`;
    if (currentPageButton) currentPageButton.textContent = String(currentPage);
    if (previousButton) previousButton.disabled = currentPage <= 1;
    if (nextButton) nextButton.disabled = currentPage >= pageCount;
    if (statusFilterLabel) statusFilterLabel.textContent = selectedState === 'all' ? 'Estado: todos' : selectedState === 'active' ? 'Activos' : 'Inactivos';

    const totalCount = document.getElementById('programTotalCount');
    const inUseCount = document.getElementById('programInUseCount');
    const unassignedCount = document.getElementById('programUnassignedCount');
    const installationCount = document.getElementById('programInstallationCount');
    if (totalCount) totalCount.textContent = String(allProgramas.length);
    if (inUseCount) inUseCount.textContent = String(allProgramas.filter((programa) => Number(programa.equiposAsociados) > 0).length);
    if (unassignedCount) unassignedCount.textContent = String(allProgramas.filter((programa) => Number(programa.equiposAsociados) === 0).length);
    if (installationCount) installationCount.textContent = String(allProgramas.reduce((total, programa) => total + (Number(programa.equiposAsociados) || 0), 0));
  };

  searchInput?.addEventListener('input', () => { currentPage = 1; render(); });
  statusFilter?.addEventListener('click', () => { selectedState = states[(states.indexOf(selectedState) + 1) % states.length]; currentPage = 1; render(); });
  previousButton?.addEventListener('click', () => { currentPage -= 1; render(); });
  nextButton?.addEventListener('click', () => { currentPage += 1; render(); });

  render();
});
