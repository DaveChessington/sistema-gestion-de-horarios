document.addEventListener('DOMContentLoaded', () => {
  const dataElement = document.getElementById('plantelData');
  const actionDataElement = document.getElementById('plantelActionData');
  const searchInput = document.getElementById('plantelSearch');
  const filterButton = document.getElementById('plantelStatusFilter');
  const filterLabel = filterButton?.querySelector('[data-filter-label]');
  const resetButton = document.getElementById('plantelReset');
  const tableBody = document.getElementById('plantelTableBody');
  const mobileList = document.getElementById('plantelMobileList');
  const resultCount = document.getElementById('plantelResultCount');
  const previousButton = document.getElementById('plantelPreviousPage');
  const nextButton = document.getElementById('plantelNextPage');
  const currentPageButton = document.getElementById('plantelCurrentPage');

  if (!dataElement || !tableBody || !mobileList) return;

  let plantelRecords = [];
  let actionContext = {};
  try {
    const parsedData = JSON.parse(dataElement.textContent);
    const parsedActions = JSON.parse(actionDataElement?.textContent || '{}');
    plantelRecords = Array.isArray(parsedData) ? parsedData : [];
    actionContext = parsedActions && typeof parsedActions === 'object' ? parsedActions : {};
  } catch (_error) {
    plantelRecords = [];
    actionContext = {};
  }

  const pageSize = 2;
  const states = ['all', 'active', 'inactive'];
  const stateLabels = {
    all: 'Estado: todos',
    active: 'Estado: activos',
    inactive: 'Estado: inactivos',
  };
  let selectedState = 'all';
  let currentPage = 1;

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const initials = (name) => name
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((word) => word[0]?.toUpperCase())
    .join('');

  const statusBadge = (active) => `<span class="status-badge ${active ? 'status-active' : 'status-inactive'}"><span></span>${active ? 'Activo' : 'Inactivo'}</span>`;

  const canManage = (plantel) => actionContext.role === 'COORDINADOR'
    || (actionContext.role === 'ADMIN_PLANTEL'
      && Number(actionContext.assigned_plantel_id) === Number(plantel.id));

  const actionUrl = (template, plantelId, suffix) => String(template || '')
    .replace(new RegExp(`/0/${suffix}$`), `/${plantelId}/${suffix}`);

  const actionControls = (plantel, mobile = false) => {
    const plantelId = Number(plantel.id);
    if (!plantel.activo) {
      return '<span class="text-xs text-slate-400">Registro inactivo</span>';
    }
    if (!canManage(plantel)) {
      return '<span class="inline-flex items-center gap-2 text-xs text-slate-400"><i class="fa-solid fa-lock"></i>Sin permisos</span>';
    }
    if (!Number.isInteger(plantelId) || plantelId <= 0) return '';

    const editUrl = actionUrl(actionContext.edit_url_template, plantelId, 'editar');
    const deactivateUrl = actionUrl(actionContext.deactivate_url_template, plantelId, 'desactivar');
    const editClass = mobile
      ? 'inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-semibold text-slate-600'
      : 'table-action';
    const deactivateClass = mobile
      ? 'inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs font-semibold text-red-700'
      : 'table-action table-action-danger';
    return `
      <a href="${escapeHtml(editUrl)}" class="${editClass}" aria-label="Editar ${escapeHtml(plantel.nombre)}"><i class="fa-regular fa-pen-to-square"></i>${mobile ? '<span>Editar</span>' : ''}</a>
      <form method="post" action="${escapeHtml(deactivateUrl)}" data-deactivate-plantel-form data-plantel-name="${escapeHtml(plantel.nombre)}"${mobile ? ' class="flex-1"' : ''}>
        <button type="submit" class="${deactivateClass}${mobile ? ' w-full' : ''}" aria-label="Desactivar ${escapeHtml(plantel.nombre)}"><i class="fa-regular fa-trash-can"></i>${mobile ? '<span>Desactivar</span>' : ''}</button>
      </form>`;
  };

  const tableRow = (plantel) => `
    <tr class="catalog-row">
      <td class="px-6 py-4"><div class="flex items-center gap-3"><span class="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-sm font-bold text-blue-600">${escapeHtml(initials(plantel.nombre))}</span><div><p class="text-sm font-semibold text-slate-900">${escapeHtml(plantel.nombre)}</p><p class="mt-1 text-xs text-slate-400">ID ${String(plantel.id).padStart(3, '0')}</p></div></div></td>
      <td class="px-6 py-4 text-sm text-slate-600">${escapeHtml(plantel.direccion || 'Sin dirección')}</td>
      <td class="px-6 py-4">${statusBadge(plantel.activo)}</td>
      <td class="px-6 py-4"><div class="flex items-center justify-end gap-2">${actionControls(plantel)}</div></td>
    </tr>`;

  const mobileCard = (plantel) => `
    <article class="p-5">
      <div class="flex items-start justify-between gap-3"><div class="flex items-center gap-3"><span class="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-sm font-bold text-blue-600">${escapeHtml(initials(plantel.nombre))}</span><div><h3 class="text-sm font-semibold">${escapeHtml(plantel.nombre)}</h3><p class="mt-1 text-xs text-slate-400">ID ${String(plantel.id).padStart(3, '0')}</p></div></div>${statusBadge(plantel.activo)}</div>
      <p class="mt-4 flex items-center gap-2 text-xs text-slate-500"><i class="fa-solid fa-location-dot text-slate-400"></i>${escapeHtml(plantel.direccion || 'Sin dirección')}</p>
      <div class="mt-4 flex items-center gap-2">${actionControls(plantel, true)}</div>
    </article>`;

  const filteredPlanteles = () => {
    const query = searchInput?.value.trim().toLocaleLowerCase('es') || '';
    return plantelRecords.filter((plantel) => {
      const matchesQuery = `${plantel.nombre} ${plantel.direccion}`.toLocaleLowerCase('es').includes(query);
      const matchesState = selectedState === 'all'
        || (selectedState === 'active' && plantel.activo)
        || (selectedState === 'inactive' && !plantel.activo);
      return matchesQuery && matchesState;
    });
  };

  const render = () => {
    const planteles = filteredPlanteles();
    const pageCount = Math.max(1, Math.ceil(planteles.length / pageSize));
    currentPage = Math.min(currentPage, pageCount);
    const visible = planteles.slice((currentPage - 1) * pageSize, currentPage * pageSize);

    tableBody.innerHTML = visible.length
      ? visible.map(tableRow).join('')
      : '<tr><td colspan="4" class="px-6 py-12 text-center text-sm text-slate-400">No se encontraron planteles.</td></tr>';
    mobileList.innerHTML = visible.length
      ? visible.map(mobileCard).join('')
      : '<p class="p-8 text-center text-sm text-slate-400">No se encontraron planteles.</p>';

    if (resultCount) resultCount.innerHTML = `Mostrando <span class="font-semibold text-slate-700">${visible.length}</span> de ${planteles.length} planteles`;
    if (currentPageButton) currentPageButton.textContent = String(currentPage);
    if (previousButton) previousButton.disabled = currentPage <= 1;
    if (nextButton) nextButton.disabled = currentPage >= pageCount;
    if (filterLabel) filterLabel.textContent = stateLabels[selectedState];
  };

  searchInput?.addEventListener('input', () => { currentPage = 1; render(); });
  filterButton?.addEventListener('click', () => {
    selectedState = states[(states.indexOf(selectedState) + 1) % states.length];
    currentPage = 1;
    render();
  });
  resetButton?.addEventListener('click', () => {
    if (searchInput) searchInput.value = '';
    selectedState = 'all';
    currentPage = 1;
    render();
  });
  previousButton?.addEventListener('click', () => { currentPage -= 1; render(); });
  nextButton?.addEventListener('click', () => { currentPage += 1; render(); });
  document.addEventListener('submit', (event) => {
    const form = event.target.closest('[data-deactivate-plantel-form]');
    if (!form) return;
    const plantelName = form.dataset.plantelName || 'este plantel';
    const confirmed = window.confirm(
      `¿Desactivar ${plantelName}? Sus salones y equipos asociados también quedarán inactivos.`
    );
    if (!confirmed) {
      event.preventDefault();
      return;
    }
    const button = form.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
    }
  });

  render();
});
