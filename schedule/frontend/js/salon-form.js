document.addEventListener('DOMContentLoaded', () => {
  const mockData = window.ScheduleMockData;
  const form = document.getElementById('salonForm');
  const nameInput = document.getElementById('salonName');
  const capacityInput = document.getElementById('salonCapacity');
  const descriptionInput = document.getElementById('salonDescription');
  const plantelSelect = document.getElementById('salonPlantel');
  const nameError = document.getElementById('salonNameError');
  const capacityError = document.getElementById('salonCapacityError');
  const plantelError = document.getElementById('salonPlantelError');

  if (!mockData || !form || !nameInput || !capacityInput || !plantelSelect) return;

  const activePlanteles = mockData.readPlanteles().filter((plantel) => plantel.activo);
  activePlanteles.forEach((plantel) => {
    plantelSelect.add(new Option(plantel.nombre, String(plantel.id)));
  });

  const updatePreview = () => {
    const selectedOption = plantelSelect.options[plantelSelect.selectedIndex];
    document.getElementById('salonPreviewName').textContent = nameInput.value.trim() || 'Salón pendiente';
    document.getElementById('salonPreviewPlantel').textContent = selectedOption?.value ? selectedOption.textContent : 'Plantel sin seleccionar';
    document.getElementById('salonPreviewCapacity').textContent = Number(capacityInput.value) > 0 ? `${Number(capacityInput.value)} personas` : '— personas';
  };

  [nameInput, capacityInput, plantelSelect].forEach((field) => field.addEventListener('input', updatePreview));
  plantelSelect.addEventListener('change', updatePreview);

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const numero = nameInput.value.trim();
    const capacidad = Number(capacityInput.value);
    const idPlantel = Number(plantelSelect.value);
    const validName = numero.length > 0;
    const validCapacity = Number.isFinite(capacidad) && capacidad > 0;
    const validPlantel = activePlanteles.some((plantel) => Number(plantel.id) === idPlantel);

    nameError?.classList.toggle('hidden', validName);
    capacityError?.classList.toggle('hidden', validCapacity);
    plantelError?.classList.toggle('hidden', validPlantel);
    nameInput.classList.toggle('field-error', !validName);
    capacityInput.classList.toggle('field-error', !validCapacity);
    plantelSelect.setAttribute('aria-invalid', String(!validPlantel));
    if (!validName || !validCapacity || !validPlantel) return;

    const salones = mockData.readSalones();
    salones.push({
      id: mockData.nextSalonId(salones),
      numero,
      descripcion: descriptionInput?.value.trim() || '',
      capacidad,
      idPlantel,
      activo: true,
    });
    mockData.writeSalones(salones);
    window.location.assign(form.dataset.listUrl || '/admin/salones');
  });

  updatePreview();
});
