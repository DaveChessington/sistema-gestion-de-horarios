document.addEventListener('DOMContentLoaded', () => {
  const dataElement = document.getElementById('dashboardData');
  if (!dataElement) return;

  let dashboardData;
  try {
    dashboardData = JSON.parse(dataElement.textContent);
  } catch (_error) {
    return;
  }

  const collectionBindings = {
    planteles: ['dashboardPlantelCount', 'dashboardPlantelCaption'],
    salones: ['dashboardSalonCount', 'dashboardSalonCaption'],
    equipos: ['dashboardEquipoCount', 'dashboardEquipoCaption'],
    programas: ['dashboardProgramaCount', 'dashboardProgramaCaption'],
    usuarios: ['dashboardUsuarioCount', 'dashboardUsuarioCaption'],
  };

  Object.entries(collectionBindings).forEach(([name, [countId, captionId]]) => {
    const metrics = dashboardData.collections?.[name] || { total: 0, active: 0 };
    const countElement = document.getElementById(countId);
    const captionElement = document.getElementById(captionId);
    if (countElement) countElement.textContent = String(metrics.total);
    if (captionElement) {
      captionElement.textContent = `${metrics.active} ${metrics.active === 1 ? 'activo' : 'activos'} de ${metrics.total}`;
    }
  });

  const values = {
    dashboardRecordCount: dashboardData.totals?.records,
    dashboardActiveCount: dashboardData.totals?.active,
    dashboardInactiveCount: dashboardData.totals?.inactive,
    dashboardUnassignedEquipmentCount: dashboardData.totals?.unassigned_equipment,
    dashboardBookingCount: dashboardData.booking?.total,
    dashboardApprovedBookingCount: dashboardData.booking?.approved,
    dashboardPendingBookingCount: dashboardData.booking?.pending,
  };
  Object.entries(values).forEach(([elementId, value]) => {
    const element = document.getElementById(elementId);
    if (element) element.textContent = String(Number.isInteger(value) ? value : 0);
  });

  const services = Object.values(dashboardData.services || {});
  const connectedServices = services.filter(Boolean).length;
  const statusLabel = document.getElementById('dashboardDataStatusLabel');
  const statusDot = document.getElementById('dashboardDataStatusDot');
  const scopeLabel = dashboardData.scope === 'plantel' ? 'alcance del plantel' : 'alcance global';
  if (statusLabel) {
    statusLabel.textContent = `${connectedServices} de ${services.length} servicios conectados · ${scopeLabel}`;
  }
  if (statusDot) {
    statusDot.classList.remove('bg-slate-400');
    statusDot.classList.add(connectedServices === services.length ? 'bg-emerald-400' : 'bg-amber-400');
  }
});
