document.addEventListener('DOMContentLoaded', () => {
  const mockData = window.ScheduleMockData;
  if (!mockData) return;

  const collections = [
    {
      items: mockData.readPlanteles(),
      countId: 'dashboardPlantelCount',
      captionId: 'dashboardPlantelCaption',
    },
    {
      items: mockData.readSalones(),
      countId: 'dashboardSalonCount',
      captionId: 'dashboardSalonCaption',
    },
    {
      items: mockData.readEquipos(),
      countId: 'dashboardEquipoCount',
      captionId: 'dashboardEquipoCaption',
    },
    {
      items: mockData.readProgramas(),
      countId: 'dashboardProgramaCount',
      captionId: 'dashboardProgramaCaption',
    },
    {
      items: mockData.readUsuarios(),
      countId: 'dashboardUsuarioCount',
      captionId: 'dashboardUsuarioCaption',
    },
  ];

  collections.forEach(({ items, countId, captionId }) => {
    const activeCount = items.filter((item) => item.activo).length;
    const count = document.getElementById(countId);
    const caption = document.getElementById(captionId);
    if (count) count.textContent = String(items.length);
    if (caption) caption.textContent = `${activeCount} ${activeCount === 1 ? 'activo' : 'activos'} de ${items.length}`;
  });

  const allItems = collections.flatMap(({ items }) => items);
  const activeCount = allItems.filter((item) => item.activo).length;
  const inactiveCount = allItems.length - activeCount;
  const unassignedEquipmentCount = mockData.readEquipos().filter((equipo) => !equipo.idSalon).length;

  const recordCount = document.getElementById('dashboardRecordCount');
  const activeTotal = document.getElementById('dashboardActiveCount');
  const inactiveTotal = document.getElementById('dashboardInactiveCount');
  const unassignedTotal = document.getElementById('dashboardUnassignedEquipmentCount');
  const dataStatusLabel = document.getElementById('dashboardDataStatusLabel');
  if (recordCount) recordCount.textContent = String(allItems.length);
  if (activeTotal) activeTotal.textContent = String(activeCount);
  if (inactiveTotal) inactiveTotal.textContent = String(inactiveCount);
  if (unassignedTotal) unassignedTotal.textContent = String(unassignedEquipmentCount);
  if (dataStatusLabel) dataStatusLabel.textContent = 'Datos mock sincronizados';
});
