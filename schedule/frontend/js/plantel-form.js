document.addEventListener('DOMContentLoaded', () => {
  const mockData = window.ScheduleMockData;
  const form = document.getElementById('plantelForm');
  const nameInput = document.getElementById('plantelName');
  const addressInput = document.getElementById('plantelAddress');
  const nameError = document.getElementById('plantelNameError');
  const previewName = document.getElementById('plantelPreviewName');
  const previewAddress = document.getElementById('plantelPreviewAddress');

  if (!mockData || !form || !nameInput || !addressInput) return;

  const updatePreview = () => {
    if (previewName) previewName.textContent = nameInput.value.trim() || 'Nombre pendiente';
    if (previewAddress) previewAddress.textContent = addressInput.value.trim() || 'Dirección pendiente';
  };

  nameInput.addEventListener('input', () => {
    nameError?.classList.add('hidden');
    nameInput.classList.remove('field-error');
    updatePreview();
  });
  addressInput.addEventListener('input', updatePreview);

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const nombre = nameInput.value.trim();
    const direccion = addressInput.value.trim();
    const isValid = nombre.length > 0;

    nameError?.classList.toggle('hidden', isValid);
    nameInput.classList.toggle('field-error', !isValid);
    nameInput.setAttribute('aria-invalid', String(!isValid));
    if (!isValid) {
      nameInput.focus();
      return;
    }

    const planteles = mockData.readPlanteles();
    planteles.push({
      id: mockData.nextPlantelId(planteles),
      nombre,
      direccion,
      activo: true,
    });
    mockData.writePlanteles(planteles);
    window.location.assign(form.dataset.listUrl || '/admin/planteles');
  });

  updatePreview();
});
