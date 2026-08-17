document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('userForm');
  const nameInput = document.getElementById('userName');
  const lastNameInput = document.getElementById('userLastName');
  const emailInput = document.getElementById('userEmail');
  const passwordInput = document.getElementById('userPassword');
  const confirmInput = document.getElementById('userPasswordConfirm');
  const roleSelect = document.getElementById('userRole');
  const plantelSelect = document.getElementById('userPlantel');

  if (!form || !nameInput || !lastNameInput || !emailInput || !passwordInput || !confirmInput || !roleSelect || !plantelSelect) return;
  const isEdit = form.dataset.editMode === 'true';
  const requiresPlantel = form.dataset.requiresPlantel === 'true';

  const roleLabels = {
    COORDINADOR: 'Coordinador',
    ADMIN_PLANTEL: 'Admin. plantel',
    DOCENTE: 'Docente',
    ALUMNO: 'Alumno',
  };
  const toggleError = (input, errorId, valid, containerSelector = null) => {
    document.getElementById(errorId)?.classList.toggle('hidden', valid);
    const target = containerSelector ? input.closest(containerSelector) : input;
    target?.classList.toggle('field-error', !valid);
    input.setAttribute('aria-invalid', String(!valid));
  };

  const updatePreview = () => {
    const nombre = nameInput.value.trim();
    const apellido = lastNameInput.value.trim();
    const completeName = `${nombre} ${apellido}`.trim();
    const initials = [nombre, apellido].filter(Boolean).map((value) => value.charAt(0).toLocaleUpperCase('es')).join('') || 'NU';
    const selectedPlantel = plantelSelect.options[plantelSelect.selectedIndex];
    document.getElementById('userPreviewInitials').textContent = initials;
    document.getElementById('userPreviewName').textContent = completeName || 'Nuevo usuario';
    document.getElementById('userPreviewEmail').textContent = emailInput.value.trim() || 'Correo pendiente';
    document.getElementById('userPreviewRole').textContent = roleLabels[roleSelect.value] || 'Sin seleccionar';
    document.getElementById('userPreviewPlantel').textContent = selectedPlantel?.value ? selectedPlantel.textContent : (roleSelect.value === 'COORDINADOR' ? 'Acceso global' : 'Sin seleccionar');
  };

  [nameInput, lastNameInput, emailInput].forEach((input) => input.addEventListener('input', updatePreview));
  roleSelect.addEventListener('change', updatePreview);
  plantelSelect.addEventListener('change', updatePreview);

  form.addEventListener('submit', (event) => {
    const nombre = nameInput.value.trim();
    const apellido = lastNameInput.value.trim();
    const correo = emailInput.value.trim().toLocaleLowerCase('es');
    const password = passwordInput.value;
    const rol = roleSelect.value;
    const idPlantel = plantelSelect.value ? Number(plantelSelect.value) : null;

    const validName = nombre.length > 0;
    const validLastName = apellido.length > 0;
    const validEmailFormat = /.+@.+\..+/.test(correo);
    const validEmail = validEmailFormat;
    const strongPassword = password.length >= 12
      && new TextEncoder().encode(password).length <= 72
      && /[A-Z]/.test(password)
      && /[a-z]/.test(password)
      && /\d/.test(password)
      && /[^A-Za-z0-9]/.test(password);
    const validPassword = isEdit ? password.length === 0 || strongPassword : strongPassword;
    const validConfirmation = validPassword && confirmInput.value === password;
    const validRole = Object.hasOwn(roleLabels, rol);
    const validPlantel = (!requiresPlantel && rol !== 'ADMIN_PLANTEL') || Number.isInteger(idPlantel);

    const emailError = document.getElementById('userEmailError');
    if (emailError) emailError.textContent = 'Ingresa un correo válido.';
    toggleError(nameInput, 'userNameError', validName);
    toggleError(lastNameInput, 'userLastNameError', validLastName);
    toggleError(emailInput, 'userEmailError', validEmail, '.form-input-icon');
    toggleError(passwordInput, 'userPasswordError', validPassword, '.form-input-icon');
    toggleError(confirmInput, 'userPasswordConfirmError', validConfirmation, '.form-input-icon');
    toggleError(roleSelect, 'userRoleError', validRole, '.form-select');
    toggleError(plantelSelect, 'userPlantelError', validPlantel, '.form-select');

    if (!validName || !validLastName || !validEmail || !validPassword || !validConfirmation || !validRole || !validPlantel) {
      event.preventDefault();
      return;
    }

    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i>${isEdit ? 'Guardando...' : 'Registrando...'}`;
    }
  });

  updatePreview();
});
