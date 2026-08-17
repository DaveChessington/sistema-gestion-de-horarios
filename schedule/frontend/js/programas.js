document.addEventListener('DOMContentLoaded', () => {
  const programDataElement = document.getElementById('programData');
  const equipmentDataElement = document.getElementById('programEquipmentData');
  const actionDataElement = document.getElementById('programActionData');
  const searchInput = document.getElementById('programSearch');
  const statusFilter = document.getElementById('programStatusFilter');
  const statusFilterLabel = statusFilter?.querySelector('[data-filter-label]');
  const cardGrid = document.getElementById('programCardGrid');
  const resultCount = document.getElementById('programResultCount');
  const previousButton = document.getElementById('programPreviousPage');
  const nextButton = document.getElementById('programNextPage');
  const currentPageButton = document.getElementById('programCurrentPage');

  if (!programDataElement || !equipmentDataElement || !cardGrid) return;

  let programRecords = [];
  let equipmentRecords = [];
  let actionContext = {};
  try {
    const parsedPrograms = JSON.parse(programDataElement.textContent);
    const parsedEquipment = JSON.parse(equipmentDataElement.textContent);
    const parsedActions = actionDataElement ? JSON.parse(actionDataElement.textContent) : {};
    programRecords = Array.isArray(parsedPrograms) ? parsedPrograms : [];
    equipmentRecords = Array.isArray(parsedEquipment) ? parsedEquipment : [];
    actionContext = parsedActions && typeof parsedActions === 'object' ? parsedActions : {};
  } catch (_error) {
    programRecords = [];
    equipmentRecords = [];
    actionContext = {};
  }

  const pageSize = 3;
  const states = ['all', 'active', 'inactive'];
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
    return programRecords.filter((programa) => {
      const matchesQuery = `${programa.nombre} ${programa.descripcion}`.toLocaleLowerCase('es').includes(query);
      const matchesState = selectedState === 'all'
        || (selectedState === 'active' && programa.activo)
        || (selectedState === 'inactive' && !programa.activo);
      return matchesQuery && matchesState;
    });
  };

  const associationCount = (programId) => equipmentRecords.reduce((total, equipo) => {
    const isAssociated = (Array.isArray(equipo.programas) ? equipo.programas : [])
      .some((programa) => Number(programa.id_programa) === Number(programId));
    return total + (isAssociated ? 1 : 0);
  }, 0);

  const actionUrl = (template, programId) => String(template || '').replace(/\/0(?=\/|$)/, `/${programId}`);
  const actionControls = (programa) => {
    if (!programa.activo) return '<span class="text-xs text-slate-400">Sin acciones</span>';
    const associateUrl = escapeHtml(actionUrl(actionContext.associate_url_template, programa.id_programa));
    const editUrl = escapeHtml(actionUrl(actionContext.edit_url_template, programa.id_programa));
    const deactivateUrl = escapeHtml(actionUrl(actionContext.deactivate_url_template, programa.id_programa));
    const label = escapeHtml(programa.nombre);
    return `<div class="flex gap-2"><a href="${associateUrl}" class="table-action" aria-label="Asociar equipos a ${label}"><i class="fa-solid fa-link"></i></a><a href="${editUrl}" class="table-action" aria-label="Editar ${label}"><i class="fa-regular fa-pen-to-square"></i></a><form method="post" action="${deactivateUrl}" data-program-deactivate data-program-label="${label}"><button type="submit" class="table-action table-action-danger" aria-label="Desactivar ${label}"><i class="fa-regular fa-trash-can"></i></button></form></div>`;
  };

  const programVisual = (name) => {
    const normalized = String(name || '').toLocaleLowerCase('es');
    if (normalized.includes('python')) return { icon: 'fa-brands fa-python', color: 'bg-sky-500' };
    if (normalized.includes('postgres') || normalized.includes('sql')) return { icon: 'fa-solid fa-database', color: 'bg-indigo-600' };
    if (normalized.includes('docker')) return { icon: 'fa-brands fa-docker', color: 'bg-slate-800' };
    if (normalized.includes('git')) return { icon: 'fa-brands fa-git-alt', color: 'bg-orange-600' };
    if (normalized.includes('node')) return { icon: 'fa-brands fa-node-js', color: 'bg-emerald-600' };
    if (normalized.includes('code') || normalized.includes('editor')) return { icon: 'fa-solid fa-code', color: 'bg-blue-600' };
    return { icon: 'fa-solid fa-box', color: 'bg-amber-500' };
  };

  const programCard = (programa) => {
    const associated = associationCount(programa.id_programa);
    const { icon, color } = programVisual(programa.nombre);
    const associationText = associated === 0 ? 'Sin asignar' : `${associated} ${associated === 1 ? 'estación' : 'estaciones'}`;

    return `
      <article class="software-card">
        <div class="flex items-start justify-between"><span class="software-logo ${color} text-white"><i class="${icon}"></i></span><span class="status-badge ${programa.activo ? 'status-active' : 'status-inactive'}"><span></span>${programa.activo ? 'Activo' : 'Inactivo'}</span></div>
        <h3 class="mt-5 text-base font-semibold">${escapeHtml(programa.nombre)}</h3>
        <p class="mt-2 min-h-10 text-xs leading-5 text-slate-500">${escapeHtml(programa.descripcion || 'Sin descripción')}</p>
        <div class="mt-5 flex items-center justify-between border-t border-slate-100 pt-4"><div><p class="resource-label">Equipos asociados</p><p class="resource-value">${associationText}</p></div>${actionControls(programa)}</div>
      </article>`;
  };

  const render = () => {
    const allProgramas = programRecords;
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
    if (inUseCount) inUseCount.textContent = String(allProgramas.filter((programa) => associationCount(programa.id_programa) > 0).length);
    if (unassignedCount) unassignedCount.textContent = String(allProgramas.filter((programa) => associationCount(programa.id_programa) === 0).length);
    if (installationCount) installationCount.textContent = String(allProgramas.reduce((total, programa) => total + associationCount(programa.id_programa), 0));
  };

  searchInput?.addEventListener('input', () => { currentPage = 1; render(); });
  statusFilter?.addEventListener('click', () => { selectedState = states[(states.indexOf(selectedState) + 1) % states.length]; currentPage = 1; render(); });
  previousButton?.addEventListener('click', () => { currentPage -= 1; render(); });
  nextButton?.addEventListener('click', () => { currentPage += 1; render(); });
  document.addEventListener('submit', (event) => {
    const deactivateForm = event.target.closest('[data-program-deactivate]');
    if (!deactivateForm) return;
    const label = deactivateForm.dataset.programLabel || 'este programa';
    if (!window.confirm(`¿Desactivar ${label}? Dejará de mostrarse como software disponible en los equipos.`)) {
      event.preventDefault();
    }
  });

  render();
});
