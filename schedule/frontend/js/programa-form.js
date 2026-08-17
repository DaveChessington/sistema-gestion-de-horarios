document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('programForm');
  const nameInput = document.getElementById('programName');
  const descriptionInput = document.getElementById('programDescription');
  const nameError = document.getElementById('programNameError');
  const previewName = document.getElementById('programPreviewName');
  const previewDescription = document.getElementById('programPreviewDescription');

  if (!form || !nameInput) return;

  const updatePreview = () => {
    if (previewName) previewName.textContent = nameInput.value.trim() || 'Programa pendiente';
    if (previewDescription) previewDescription.textContent = descriptionInput?.value.trim() || 'Descripción pendiente';
  };

  nameInput.addEventListener('input', updatePreview);
  descriptionInput?.addEventListener('input', updatePreview);

  form.addEventListener('submit', (event) => {
    const nombre = nameInput.value.trim();
    const validName = nombre.length > 0;

    if (nameError) {
      nameError.textContent = validName ? '' : 'Escribe el nombre del programa.';
      nameError.classList.toggle('hidden', validName);
    }
    nameInput.classList.toggle('field-error', !validName);
    nameInput.setAttribute('aria-invalid', String(!validName));
    if (!validName) {
      event.preventDefault();
      nameInput.focus();
      return;
    }

    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i>${form.dataset.submitProgress || 'Guardando...'}`;
    }
  });

  updatePreview();
});
