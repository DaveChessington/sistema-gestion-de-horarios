document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('scheduleForm');
  const plantelSelect = document.getElementById('schedulePlantel');
  const salonSelect = document.getElementById('scheduleSalon');
  const dateInput = document.getElementById('scheduleDate');
  const slotSelect = document.getElementById('scheduleSlot');
  const eventTypeSelect = document.getElementById('scheduleEventType');
  const subjectInput = document.getElementById('scheduleSubject');
  const studentsInput = document.getElementById('scheduleStudents');
  const salonDataElement = document.getElementById('scheduleSalonData');

  if (!form || !plantelSelect || !salonSelect || !dateInput || !slotSelect || !eventTypeSelect) return;

  let salons = [];
  try {
    const parsedSalons = JSON.parse(salonDataElement?.textContent || '[]');
    salons = Array.isArray(parsedSalons) ? parsedSalons : [];
  } catch {
    salons = [];
  }

  const selectedSalonId = salonSelect.dataset.selectedSalon || '';
  const selectedSalon = () => salons.find(salon => String(salon.id_salon) === salonSelect.value);

  const renderSalons = (preferredId = '') => {
    const availableSalons = salons.filter(salon => String(salon.id_plantel) === plantelSelect.value);
    salonSelect.replaceChildren(new Option('Seleccionar salón', ''));
    availableSalons.forEach((salon) => {
      const label = salon.capacidad
        ? `${salon.numero} · ${salon.capacidad} personas`
        : salon.numero;
      salonSelect.add(new Option(label, String(salon.id_salon)));
    });
    if (availableSalons.some(salon => String(salon.id_salon) === preferredId)) {
      salonSelect.value = preferredId;
    }
  };

  const updatePreview = () => {
    const plantelOption = plantelSelect.options[plantelSelect.selectedIndex];
    const salonOption = salonSelect.options[salonSelect.selectedIndex];
    const slotOption = slotSelect.options[slotSelect.selectedIndex];
    const salon = selectedSalon();
    const subject = subjectInput?.value.trim() || 'Actividad pendiente';
    const location = plantelSelect.value && salonSelect.value
      ? `${plantelOption.textContent} · ${salonOption.textContent.split(' · ')[0]}`
      : 'Ubicación sin seleccionar';
    const reservationDate = dateInput.value
      ? new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${dateInput.value}T00:00:00Z`))
      : '';

    document.getElementById('schedulePreviewSubject').textContent = subject;
    document.getElementById('schedulePreviewLocation').textContent = location;
    document.getElementById('schedulePreviewTime').textContent = reservationDate && slotSelect.value
      ? `${reservationDate} · ${slotOption.textContent}`
      : 'Pendiente';
    document.getElementById('schedulePreviewCapacity').textContent = salon?.capacidad
      ? `${salon.capacidad} personas`
      : '— personas';
    studentsInput?.setAttribute('max', String(salon?.capacidad || ''));
  };

  const fieldState = (field, errorId, valid) => {
    document.getElementById(errorId)?.classList.toggle('hidden', valid);
    field.classList.toggle('field-error', !valid);
    field.setAttribute('aria-invalid', String(!valid));
  };

  plantelSelect.addEventListener('change', () => {
    renderSalons();
    updatePreview();
  });
  salonSelect.addEventListener('change', updatePreview);
  [dateInput, slotSelect, eventTypeSelect, subjectInput, studentsInput].forEach((field) => {
    field?.addEventListener('input', updatePreview);
    field?.addEventListener('change', updatePreview);
  });

  form.addEventListener('submit', (event) => {
    const salon = selectedSalon();
    const studentValue = studentsInput?.value.trim() || '';
    const studentCount = Number(studentValue);
    const validPlantel = plantelSelect.value.length > 0;
    const validSalon = Boolean(salon) && String(salon.id_plantel) === plantelSelect.value;
    const validDate = dateInput.value.length > 0 && !Number.isNaN(Date.parse(`${dateInput.value}T00:00:00Z`));
    const validSlot = slotSelect.value.length > 0;
    const validEventType = eventTypeSelect.value.length > 0;
    const validStudents = studentValue.length === 0
      || (Number.isInteger(studentCount) && studentCount > 0 && studentCount <= Number(salon?.capacidad || 0));

    fieldState(plantelSelect, 'schedulePlantelError', validPlantel);
    fieldState(salonSelect, 'scheduleSalonError', validSalon);
    fieldState(dateInput, 'scheduleDateError', validDate);
    fieldState(slotSelect, 'scheduleSlotError', validSlot);
    fieldState(eventTypeSelect, 'scheduleEventTypeError', validEventType);
    if (studentsInput) fieldState(studentsInput, 'scheduleStudentsError', validStudents);

    if (!validPlantel || !validSalon || !validDate || !validSlot || !validEventType || !validStudents) {
      event.preventDefault();
      const firstInvalid = [
        [plantelSelect, validPlantel], [salonSelect, validSalon], [dateInput, validDate],
        [slotSelect, validSlot], [eventTypeSelect, validEventType], [studentsInput, validStudents]
      ].find(([, valid]) => !valid)?.[0];
      firstInvalid?.focus();
      return;
    }

    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i>Enviando...';
    }
  });

  renderSalons(selectedSalonId);
  updatePreview();
});
