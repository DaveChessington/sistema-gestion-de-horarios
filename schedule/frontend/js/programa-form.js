document.addEventListener('DOMContentLoaded', () => {
  const mockData = window.ScheduleMockData;
  const form = document.getElementById('programForm');
  const nameInput = document.getElementById('programName');
  const descriptionInput = document.getElementById('programDescription');
  const nameError = document.getElementById('programNameError');
  const previewName = document.getElementById('programPreviewName');
  const previewDescription = document.getElementById('programPreviewDescription');

  if (!mockData || !form || !nameInput) return;

  const updatePreview = () => {
    if (previewName) previewName.textContent = nameInput.value.trim() || 'Programa pendiente';
    if (previewDescription) previewDescription.textContent = descriptionInput?.value.trim() || 'Descripción pendiente';
  };

  nameInput.addEventListener('input', updatePreview);
  descriptionInput?.addEventListener('input', updatePreview);

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const nombre = nameInput.value.trim();
    const validName = nombre.length > 0;

    if (nameError) {
      nameError.textContent = validName ? '' : 'Escribe el nombre del programa.';
      nameError.classList.toggle('hidden', validName);
    }
    nameInput.classList.toggle('field-error', !validName);
    nameInput.setAttribute('aria-invalid', String(!validName));
    if (!validName) {
      nameInput.focus();
      return;
    }

    const programas = mockData.readProgramas();
    programas.push({
      id: mockData.nextProgramaId(programas),
      nombre,
      descripcion: descriptionInput?.value.trim() || '',
      activo: true,
      equiposAsociados: 0,
      icono: 'fa-solid fa-box',
      color: 'bg-amber-500',
    });
    mockData.writeProgramas(programas);
    window.location.assign(form.dataset.listUrl || '/admin/programas');
  });

  updatePreview();
});
