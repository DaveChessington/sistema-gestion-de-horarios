document.addEventListener('DOMContentLoaded', () => {
  const mockData = window.ScheduleMockData;
  const searchInput = document.getElementById('userSearch');
  const roleFilter = document.getElementById('userRoleFilter');
  const plantelFilter = document.getElementById('userPlantelFilter');
  const statusFilter = document.getElementById('userStatusFilter');
  const tableBody = document.getElementById('userTableBody');
  const mobileGrid = document.getElementById('userMobileGrid');
  const resultCount = document.getElementById('userResultCount');
  const previousButton = document.getElementById('userPreviousPage');
  const nextButton = document.getElementById('userNextPage');
  const currentPageButton = document.getElementById('userCurrentPage');

  if (!mockData || !tableBody || !mobileGrid) return;

  const roles = {
    COORDINADOR: { label: 'Coordinador', className: 'role-coordinator', avatar: 'bg-blue-100 text-blue-700' },
    ADMIN_PLANTEL: { label: 'Admin. plantel', className: 'role-campus', avatar: 'bg-violet-100 text-violet-700' },
    DOCENTE: { label: 'Docente', className: 'role-teacher', avatar: 'bg-emerald-100 text-emerald-700' },
    ALUMNO: { label: 'Alumno', className: 'role-student', avatar: 'bg-amber-100 text-amber-700' },
  };
  const planteles = mockData.readPlanteles();
  const roleChoices = [null, ...Object.keys(roles)];
  const plantelChoices = [null, ...planteles.map((plantel) => Number(plantel.id))];
  const states = ['all', 'active', 'inactive'];
  const pageSize = 4;
  let selectedRoleIndex = 0;
  let selectedPlantelIndex = 0;
  let selectedState = 'all';
  let currentPage = 1;

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const fullName = (usuario) => `${usuario.nombre || ''} ${usuario.apellido || ''}`.trim();
  const initials = (usuario) => [usuario.nombre, usuario.apellido]
    .filter(Boolean)
    .map((value) => String(value).trim().charAt(0).toLocaleUpperCase('es'))
    .join('') || 'NU';
  const plantelFor = (usuario) => planteles.find((plantel) => Number(plantel.id) === Number(usuario.idPlantel));
  const roleFor = (usuario) => roles[usuario.rol] || roles.ALUMNO;

  const filteredUsuarios = () => {
    const query = searchInput?.value.trim().toLocaleLowerCase('es') || '';
    const selectedRole = roleChoices[selectedRoleIndex];
    const selectedPlantel = plantelChoices[selectedPlantelIndex];
    return mockData.readUsuarios().filter((usuario) => {
      const searchable = `${fullName(usuario)} ${usuario.correo}`.toLocaleLowerCase('es');
      const matchesRole = selectedRole === null || usuario.rol === selectedRole;
      const matchesPlantel = selectedPlantel === null || Number(usuario.idPlantel) === selectedPlantel;
      const matchesState = selectedState === 'all'
        || (selectedState === 'active' && usuario.activo)
        || (selectedState === 'inactive' && !usuario.activo);
      return searchable.includes(query) && matchesRole && matchesPlantel && matchesState;
    });
  };

  const tableRow = (usuario) => {
    const role = roleFor(usuario);
    const plantel = plantelFor(usuario);
    return `
      <tr class="catalog-row">
        <td class="px-6 py-4"><div class="flex items-center gap-3"><span class="user-avatar ${role.avatar}">${escapeHtml(initials(usuario))}</span><div><p class="text-sm font-semibold">${escapeHtml(fullName(usuario))}</p><p class="mt-1 text-xs text-slate-400">ID ${escapeHtml(usuario.id)}</p></div></div></td>
        <td class="px-6 py-4 text-sm text-slate-600">${escapeHtml(usuario.correo)}</td>
        <td class="px-6 py-4"><span class="role-badge ${role.className}">${role.label}</span></td>
        <td class="px-6 py-4 text-sm font-medium text-slate-600">${escapeHtml(plantel?.nombre || (usuario.rol === 'COORDINADOR' ? 'Acceso global' : 'Sin asignar'))}</td>
        <td class="px-6 py-4"><span class="status-badge ${usuario.activo ? 'status-active' : 'status-inactive'}"><span></span>${usuario.activo ? 'Activo' : 'Inactivo'}</span></td>
        <td class="px-6 py-4"><div class="flex justify-end gap-2"><button type="button" aria-disabled="true" class="table-action" aria-label="Ver"><i class="fa-regular fa-eye"></i></button><button type="button" aria-disabled="true" class="table-action" aria-label="Editar"><i class="fa-regular fa-pen-to-square"></i></button><button type="button" aria-disabled="true" class="table-action table-action-danger" aria-label="Eliminar"><i class="fa-regular fa-trash-can"></i></button></div></td>
      </tr>`;
  };

  const mobileCard = (usuario) => {
    const role = roleFor(usuario);
    const plantel = plantelFor(usuario);
    return `
      <article class="user-card">
        <div class="flex items-start justify-between gap-3"><div class="flex min-w-0 items-center gap-3"><span class="user-avatar ${role.avatar}">${escapeHtml(initials(usuario))}</span><div class="min-w-0"><h3 class="text-sm font-semibold">${escapeHtml(fullName(usuario))}</h3><p class="mt-1 truncate text-xs text-slate-400">${escapeHtml(usuario.correo)}</p></div></div><span class="status-badge ${usuario.activo ? 'status-active' : 'status-inactive'}"><span></span>${usuario.activo ? 'Activo' : 'Inactivo'}</span></div>
        <div class="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-4"><span class="role-badge ${role.className}">${role.label}</span><span class="text-xs text-slate-500">${escapeHtml(plantel?.nombre || (usuario.rol === 'COORDINADOR' ? 'Acceso global' : 'Sin asignar'))}</span></div>
      </article>`;
  };

  const render = () => {
    const allUsuarios = mockData.readUsuarios();
    const usuarios = filteredUsuarios();
    const pages = Math.max(1, Math.ceil(usuarios.length / pageSize));
    currentPage = Math.min(currentPage, pages);
    const visible = usuarios.slice((currentPage - 1) * pageSize, currentPage * pageSize);
    const selectedRole = roleChoices[selectedRoleIndex];
    const selectedPlantel = plantelChoices[selectedPlantelIndex];

    tableBody.innerHTML = visible.length ? visible.map(tableRow).join('') : '<tr><td colspan="6" class="px-6 py-12 text-center text-sm text-slate-400">No se encontraron usuarios.</td></tr>';
    mobileGrid.innerHTML = visible.length ? visible.map(mobileCard).join('') : '<p class="py-10 text-center text-sm text-slate-400">No se encontraron usuarios.</p>';
    if (resultCount) resultCount.innerHTML = `Mostrando <strong class="text-slate-700">${visible.length} de ${usuarios.length}</strong> usuarios`;
    if (currentPageButton) currentPageButton.textContent = String(currentPage);
    if (previousButton) previousButton.disabled = currentPage <= 1;
    if (nextButton) nextButton.disabled = currentPage >= pages;

    const roleLabel = roleFilter?.querySelector('[data-filter-label]');
    const plantelLabel = plantelFilter?.querySelector('[data-filter-label]');
    const statusLabel = statusFilter?.querySelector('[data-filter-label]');
    if (roleLabel) roleLabel.textContent = selectedRole === null ? 'Rol: todos' : roles[selectedRole].label;
    if (plantelLabel) plantelLabel.textContent = selectedPlantel === null ? 'Plantel: todos' : planteles.find((plantel) => Number(plantel.id) === selectedPlantel)?.nombre || 'Plantel';
    if (statusLabel) statusLabel.textContent = selectedState === 'all' ? 'Estado: todos' : selectedState === 'active' ? 'Activos' : 'Inactivos';

    const totalCount = document.getElementById('userTotalCount');
    const coordinatorCount = document.getElementById('userCoordinatorCount');
    const campusAdminCount = document.getElementById('userCampusAdminCount');
    const academicCount = document.getElementById('userAcademicCount');
    const inactiveCount = document.getElementById('userInactiveCount');
    if (totalCount) totalCount.textContent = String(allUsuarios.length);
    if (coordinatorCount) coordinatorCount.textContent = String(allUsuarios.filter((usuario) => usuario.rol === 'COORDINADOR').length);
    if (campusAdminCount) campusAdminCount.textContent = String(allUsuarios.filter((usuario) => usuario.rol === 'ADMIN_PLANTEL').length);
    if (academicCount) academicCount.textContent = String(allUsuarios.filter((usuario) => ['DOCENTE', 'ALUMNO'].includes(usuario.rol)).length);
    if (inactiveCount) inactiveCount.textContent = String(allUsuarios.filter((usuario) => !usuario.activo).length);
  };

  searchInput?.addEventListener('input', () => { currentPage = 1; render(); });
  roleFilter?.addEventListener('click', () => { selectedRoleIndex = (selectedRoleIndex + 1) % roleChoices.length; currentPage = 1; render(); });
  plantelFilter?.addEventListener('click', () => { selectedPlantelIndex = (selectedPlantelIndex + 1) % plantelChoices.length; currentPage = 1; render(); });
  statusFilter?.addEventListener('click', () => { selectedState = states[(states.indexOf(selectedState) + 1) % states.length]; currentPage = 1; render(); });
  previousButton?.addEventListener('click', () => { currentPage -= 1; render(); });
  nextButton?.addEventListener('click', () => { currentPage += 1; render(); });

  render();
});
