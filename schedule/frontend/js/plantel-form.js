document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('plantelForm');
  const nameInput = document.getElementById('plantelName');
  const addressInput = document.getElementById('plantelAddress');
  const nameError = document.getElementById('plantelNameError');
  const previewName = document.getElementById('plantelPreviewName');
  const previewAddress = document.getElementById('plantelPreviewAddress');

  if (!form || !nameInput || !addressInput) return;

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
    const nombre = nameInput.value.trim();
    const isValid = nombre.length > 0;

    nameError?.classList.toggle('hidden', isValid);
    nameInput.classList.toggle('field-error', !isValid);
    nameInput.setAttribute('aria-invalid', String(!isValid));
    if (!isValid) {
      event.preventDefault();
      nameInput.focus();
      return;
    }

    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = true;
      const progressLabel = form.dataset.submitProgress || 'Procesando...';
      submitButton.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i>${progressLabel}`;
    }
  });

  updatePreview();
});
