document.addEventListener('DOMContentLoaded', () => {
  const equipmentDataElement = document.getElementById('equipmentData');
  const salonDataElement = document.getElementById('equipmentSalonData');
  const plantelDataElement = document.getElementById('equipmentPlantelData');
  const actionDataElement = document.getElementById('equipmentActionData');
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

  if (!equipmentDataElement || !salonDataElement || !plantelDataElement || !tableBody || !mobileGrid) return;

  let equipoRecords = [];
  let salones = [];
  let planteles = [];
  let actionContext = {};
  try {
    const parsedEquipos = JSON.parse(equipmentDataElement.textContent);
    const parsedSalones = JSON.parse(salonDataElement.textContent);
    const parsedPlanteles = JSON.parse(plantelDataElement.textContent);
    const parsedActions = actionDataElement ? JSON.parse(actionDataElement.textContent) : {};
    equipoRecords = Array.isArray(parsedEquipos) ? parsedEquipos : [];
    salones = Array.isArray(parsedSalones) ? parsedSalones : [];
    planteles = Array.isArray(parsedPlanteles) ? parsedPlanteles : [];
    actionContext = parsedActions && typeof parsedActions === 'object' ? parsedActions : {};
  } catch (_error) {
    equipoRecords = [];
    salones = [];
    planteles = [];
    actionContext = {};
  }

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

  const salonFor = (equipo) => salones.find((salon) => Number(salon.id_salon) === Number(equipo.id_salon));
  const plantelFor = (salon) => planteles.find((plantel) => Number(plantel.id) === Number(salon?.id_plantel));
  const actionUrl = (template, equipoId) => String(template || '').replace(/\/0(?=\/|$)/, `/${equipoId}`);
  const canManage = (equipo) => {
    if (actionContext.role === 'COORDINADOR') return true;
    const salon = salonFor(equipo);
    return actionContext.role === 'ADMIN_PLANTEL'
      && salon
      && String(salon.id_plantel) === String(actionContext.assigned_plantel_id);
  };
  const actionControls = (equipo, compact = false) => {
    if (!equipo.activo || !canManage(equipo)) {
      return compact
        ? '<p class="mt-4 text-xs text-slate-400">Sin acciones disponibles</p>'
        : '<span class="text-xs text-slate-400">Sin acciones</span>';
    }
    const editUrl = escapeHtml(actionUrl(actionContext.edit_url_template, equipo.id_equipo));
    const deactivateUrl = escapeHtml(actionUrl(actionContext.deactivate_url_template, equipo.id_equipo));
    const label = escapeHtml(equipo.numero);
    if (compact) {
      return `<div class="mt-4 flex gap-2 border-t border-slate-100 pt-4"><a href="${editUrl}" class="button-secondary flex-1 justify-center"><i class="fa-regular fa-pen-to-square"></i>Editar</a><form method="post" action="${deactivateUrl}" data-equipment-deactivate data-equipment-label="${label}" class="flex-1"><button type="submit" class="button-secondary w-full justify-center text-red-600"><i class="fa-regular fa-trash-can"></i>Desactivar</button></form></div>`;
    }
    return `<div class="flex justify-end gap-2"><a href="${editUrl}" class="table-action" aria-label="Editar ${label}"><i class="fa-regular fa-pen-to-square"></i></a><form method="post" action="${deactivateUrl}" data-equipment-deactivate data-equipment-label="${label}"><button type="submit" class="table-action table-action-danger" aria-label="Desactivar ${label}"><i class="fa-regular fa-trash-can"></i></button></form></div>`;
  };
  const salonChoices = () => {
    const selectedPlantel = plantelChoices[selectedPlantelIndex];
    const available = selectedPlantel === null
      ? salones
      : salones.filter((salon) => Number(salon.id_plantel) === selectedPlantel);
    return [null, ...available.map((salon) => Number(salon.id_salon))];
  };

  const filteredEquipos = () => {
    const query = searchInput?.value.trim().toLocaleLowerCase('es') || '';
    const selectedPlantel = plantelChoices[selectedPlantelIndex];
    const selectedSalon = salonChoices()[selectedSalonIndex];

    return equipoRecords.filter((equipo) => {
      const salon = salonFor(equipo);
      const plantel = plantelFor(salon);
      const searchable = `${equipo.numero} ${equipo.descripcion} ${salon?.numero || ''} ${plantel?.nombre || ''}`.toLocaleLowerCase('es');
      const matchesPlantel = selectedPlantel === null || Number(plantel?.id) === selectedPlantel;
      const matchesSalon = selectedSalon === null || Number(salon?.id_salon) === selectedSalon;
      const matchesState = selectedState === 'all'
        || (selectedState === 'active' && equipo.activo)
        || (selectedState === 'inactive' && !equipo.activo);
      return searchable.includes(query) && matchesPlantel && matchesSalon && matchesState;
    });
  };

  const softwareTags = (equipo, compact = false) => {
    const associated = (Array.isArray(equipo.programas) ? equipo.programas : [])
      .filter((programa) => programa && programa.activo !== false);
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
        <td class="px-6 py-4">${actionControls(equipo)}</td>
      </tr>`;
  };

  const mobileCard = (equipo) => {
    const salon = salonFor(equipo);
    const plantel = plantelFor(salon);
    return `
      <article class="resource-card">
        <div class="flex items-start justify-between"><div class="flex items-center gap-3"><span class="resource-icon ${equipo.activo ? 'bg-violet-50 text-violet-600' : 'bg-slate-100 text-slate-500'}"><i class="fa-solid fa-computer"></i></span><div><h3 class="font-semibold">${escapeHtml(equipo.numero)}</h3><p class="mt-1 text-xs text-slate-400">${escapeHtml(salon?.numero || 'Sin salón asignado')}</p></div></div><span class="status-badge ${equipo.activo ? 'status-active' : 'status-inactive'}"><span></span>${equipo.activo ? 'Activo' : 'Inactivo'}</span></div>
        <p class="mt-4 text-xs text-slate-500">${escapeHtml(plantel?.nombre || 'Sin plantel')}</p><div class="mt-3 flex flex-wrap gap-1">${softwareTags(equipo, true)}</div>${actionControls(equipo, true)}
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
    if (salonLabel) salonLabel.textContent = selectedSalon === null ? 'Salón: todos' : salones.find((salon) => Number(salon.id_salon) === selectedSalon)?.numero || 'Salón';
    if (statusLabel) statusLabel.textContent = selectedState === 'all' ? 'Estado: todos' : selectedState === 'active' ? 'Activos' : 'Inactivos';
  };

  searchInput?.addEventListener('input', () => { currentPage = 1; render(); });
  plantelFilter?.addEventListener('click', () => { selectedPlantelIndex = (selectedPlantelIndex + 1) % plantelChoices.length; selectedSalonIndex = 0; currentPage = 1; render(); });
  salonFilter?.addEventListener('click', () => { const choices = salonChoices(); selectedSalonIndex = (selectedSalonIndex + 1) % choices.length; currentPage = 1; render(); });
  statusFilter?.addEventListener('click', () => { selectedState = states[(states.indexOf(selectedState) + 1) % states.length]; currentPage = 1; render(); });
  previousButton?.addEventListener('click', () => { currentPage -= 1; render(); });
  nextButton?.addEventListener('click', () => { currentPage += 1; render(); });
  document.addEventListener('submit', (event) => {
    const deactivateForm = event.target.closest('[data-equipment-deactivate]');
    if (!deactivateForm) return;
    const label = deactivateForm.dataset.equipmentLabel || 'este equipo';
    if (!window.confirm(`¿Desactivar ${label}? El equipo dejará de estar disponible en el inventario activo.`)) {
      event.preventDefault();
    }
  });

  render();
});
