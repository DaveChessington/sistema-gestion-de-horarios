document.addEventListener('DOMContentLoaded', () => {
  const salonDataElement = document.getElementById('equipmentFormSalonData');
  const form = document.getElementById('equipmentForm');
  const nameInput = document.getElementById('equipmentName');
  const plantelSelect = document.getElementById('equipmentPlantel');
  const salonSelect = document.getElementById('equipmentSalon');
  const nameError = document.getElementById('equipmentNameError');
  const previewName = document.getElementById('equipmentPreviewName');
  const previewLocation = document.getElementById('equipmentPreviewLocation');

  if (!salonDataElement || !form || !nameInput || !plantelSelect || !salonSelect) return;

  let salones = [];
  try {
    const parsedSalones = JSON.parse(salonDataElement.textContent);
    salones = Array.isArray(parsedSalones) ? parsedSalones : [];
  } catch (_error) {
    salones = [];
  }

  const updatePreview = () => {
    const salon = salones.find((item) => Number(item.id_salon) === Number(salonSelect.value));
    const plantelOption = Array.from(plantelSelect.options)
      .find((option) => Number(option.value) === Number(salon?.id_plantel));
    if (previewName) previewName.textContent = nameInput.value.trim() || 'Equipo pendiente';
    if (previewLocation) previewLocation.textContent = salon ? `${salon.numero} · ${plantelOption?.textContent || 'Sin plantel'}` : 'Sin ubicación seleccionada';
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
      .filter((salon) => Number(salon.id_plantel) === selectedPlantel)
      .forEach((salon) => salonSelect.add(new Option(salon.numero, String(salon.id_salon))));
    salonSelect.disabled = false;
    const requestedSalon = salonSelect.dataset.selectedSalon;
    if (requestedSalon && Array.from(salonSelect.options).some((option) => option.value === requestedSalon)) {
      salonSelect.value = requestedSalon;
    }
    updatePreview();
  };

  nameInput.addEventListener('input', updatePreview);
  plantelSelect.addEventListener('change', () => {
    salonSelect.dataset.selectedSalon = '';
    refreshSalones();
  });
  salonSelect.addEventListener('change', updatePreview);

  form.addEventListener('submit', (event) => {
    const numero = nameInput.value.trim();
    const validName = numero.length > 0;
    const requiresSalon = form.dataset.requiresSalon === 'true';
    const validSalon = (!requiresSalon && !salonSelect.value)
      || (Boolean(salonSelect.value)
        && salones.some((salon) => Number(salon.id_salon) === Number(salonSelect.value)));
    nameError?.classList.toggle('hidden', validName);
    nameInput.classList.toggle('field-error', !validName);
    nameInput.setAttribute('aria-invalid', String(!validName));
    salonSelect.setAttribute('aria-invalid', String(!validSalon));
    if (!validName || !validSalon) {
      event.preventDefault();
      if (!validName) nameInput.focus();
      else salonSelect.focus();
      return;
    }

    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i>${form.dataset.submitProgress || 'Guardando...'}`;
    }
  });

  const selectedSalon = salones.find(
    (salon) => String(salon.id_salon) === salonSelect.dataset.selectedSalon,
  );
  if (selectedSalon) plantelSelect.value = String(selectedSalon.id_plantel);
  refreshSalones();
});
