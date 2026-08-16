document.addEventListener('DOMContentLoaded', () => {
  const mockData = window.ScheduleMockData;
  const form = document.getElementById('equipmentForm');
  const nameInput = document.getElementById('equipmentName');
  const descriptionInput = document.getElementById('equipmentDescription');
  const plantelSelect = document.getElementById('equipmentPlantel');
  const salonSelect = document.getElementById('equipmentSalon');
  const nameError = document.getElementById('equipmentNameError');
  const previewName = document.getElementById('equipmentPreviewName');
  const previewLocation = document.getElementById('equipmentPreviewLocation');

  if (!mockData || !form || !nameInput || !plantelSelect || !salonSelect) return;

  const planteles = mockData.readPlanteles().filter((plantel) => plantel.activo);
  const salones = mockData.readSalones().filter((salon) => salon.activo);
  const activePrograms = mockData.readProgramas().filter((programa) => programa.activo);

  planteles.forEach((plantel) => plantelSelect.add(new Option(plantel.nombre, String(plantel.id))));

  const updatePreview = () => {
    const salon = salones.find((item) => Number(item.id) === Number(salonSelect.value));
    const plantel = planteles.find((item) => Number(item.id) === Number(salon?.idPlantel));
    if (previewName) previewName.textContent = nameInput.value.trim() || 'Equipo pendiente';
    if (previewLocation) previewLocation.textContent = salon ? `${salon.numero} · ${plantel?.nombre || 'Sin plantel'}` : 'Sin ubicación seleccionada';
  };

  const refreshSalones = () => {
    const selectedPlantel = Number(plantelSelect.value);
    salonSelect.replaceChildren(new Option('Sin salón asignado', ''));
    if (!selectedPlantel) {
      salonSelect.disabled = true;
      updatePreview();
      return;
    }
    salones
      .filter((salon) => Number(salon.idPlantel) === selectedPlantel)
      .forEach((salon) => salonSelect.add(new Option(salon.numero, String(salon.id))));
    salonSelect.disabled = false;
    updatePreview();
  };

  const programHint = document.getElementById('equipmentProgramHint');
  if (programHint) programHint.textContent = `${activePrograms.length} programas activos disponibles para asociación posterior.`;

  nameInput.addEventListener('input', updatePreview);
  plantelSelect.addEventListener('change', refreshSalones);
  salonSelect.addEventListener('change', updatePreview);

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const numero = nameInput.value.trim();
    const validName = numero.length > 0;
    nameError?.classList.toggle('hidden', validName);
    nameInput.classList.toggle('field-error', !validName);
    nameInput.setAttribute('aria-invalid', String(!validName));
    if (!validName) {
      nameInput.focus();
      return;
    }

    const equipos = mockData.readEquipos();
    equipos.push({
      id: mockData.nextEquipoId(equipos),
      numero,
      descripcion: descriptionInput?.value.trim() || '',
      idSalon: salonSelect.value ? Number(salonSelect.value) : null,
      activo: true,
      programas: [],
    });
    mockData.writeEquipos(equipos);
    window.location.assign(form.dataset.listUrl || '/admin/equipos');
  });

  refreshSalones();
});
