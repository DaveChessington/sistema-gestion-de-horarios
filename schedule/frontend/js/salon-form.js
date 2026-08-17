document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('salonForm');
  const nameInput = document.getElementById('salonName');
  const capacityInput = document.getElementById('salonCapacity');
  const plantelSelect = document.getElementById('salonPlantel');
  const nameError = document.getElementById('salonNameError');
  const capacityError = document.getElementById('salonCapacityError');
  const plantelError = document.getElementById('salonPlantelError');

  if (!form || !nameInput || !capacityInput || !plantelSelect) return;

  const updatePreview = () => {
    const selectedOption = plantelSelect.options[plantelSelect.selectedIndex];
    document.getElementById('salonPreviewName').textContent = nameInput.value.trim() || 'Salón pendiente';
    document.getElementById('salonPreviewPlantel').textContent = selectedOption?.value ? selectedOption.textContent : 'Plantel sin seleccionar';
    document.getElementById('salonPreviewCapacity').textContent = Number(capacityInput.value) > 0 ? `${Number(capacityInput.value)} personas` : '— personas';
  };

  [nameInput, capacityInput, plantelSelect].forEach((field) => field.addEventListener('input', updatePreview));
  plantelSelect.addEventListener('change', updatePreview);

  form.addEventListener('submit', (event) => {
    const numero = nameInput.value.trim();
    const capacidad = Number(capacityInput.value);
    const validName = numero.length > 0;
    const validCapacity = Number.isFinite(capacidad) && capacidad > 0;
    const validPlantel = plantelSelect.value.length > 0;

    nameError?.classList.toggle('hidden', validName);
    capacityError?.classList.toggle('hidden', validCapacity);
    plantelError?.classList.toggle('hidden', validPlantel);
    nameInput.classList.toggle('field-error', !validName);
    capacityInput.classList.toggle('field-error', !validCapacity);
    plantelSelect.classList.toggle('field-error', !validPlantel);
    plantelSelect.setAttribute('aria-invalid', String(!validPlantel));
    if (!validName || !validCapacity || !validPlantel) {
      event.preventDefault();
      if (!validName) nameInput.focus();
      else if (!validCapacity) capacityInput.focus();
      else plantelSelect.focus();
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
