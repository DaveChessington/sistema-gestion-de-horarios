document.addEventListener('DOMContentLoaded', () => {
  const mockData = window.ScheduleMockData;
  const form = document.getElementById('userForm');
  const nameInput = document.getElementById('userName');
  const lastNameInput = document.getElementById('userLastName');
  const emailInput = document.getElementById('userEmail');
  const passwordInput = document.getElementById('userPassword');
  const confirmInput = document.getElementById('userPasswordConfirm');
  const roleSelect = document.getElementById('userRole');
  const plantelSelect = document.getElementById('userPlantel');

  if (!mockData || !form || !nameInput || !lastNameInput || !emailInput || !passwordInput || !confirmInput || !roleSelect || !plantelSelect) return;

  const roleLabels = {
    COORDINADOR: 'Coordinador',
    ADMIN_PLANTEL: 'Admin. plantel',
    DOCENTE: 'Docente',
    ALUMNO: 'Alumno',
  };
  const planteles = mockData.readPlanteles().filter((plantel) => plantel.activo);
  planteles.forEach((plantel) => plantelSelect.add(new Option(plantel.nombre, String(plantel.id))));

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
    const selectedPlantel = planteles.find((plantel) => Number(plantel.id) === Number(plantelSelect.value));
    document.getElementById('userPreviewInitials').textContent = initials;
    document.getElementById('userPreviewName').textContent = completeName || 'Nuevo usuario';
    document.getElementById('userPreviewEmail').textContent = emailInput.value.trim() || 'Correo pendiente';
    document.getElementById('userPreviewRole').textContent = roleLabels[roleSelect.value] || 'Sin seleccionar';
    document.getElementById('userPreviewPlantel').textContent = selectedPlantel?.nombre || (roleSelect.value === 'COORDINADOR' ? 'Acceso global' : 'Sin seleccionar');
  };

  [nameInput, lastNameInput, emailInput].forEach((input) => input.addEventListener('input', updatePreview));
  roleSelect.addEventListener('change', updatePreview);
  plantelSelect.addEventListener('change', updatePreview);

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const nombre = nameInput.value.trim();
    const apellido = lastNameInput.value.trim();
    const correo = emailInput.value.trim().toLocaleLowerCase('es');
    const password = passwordInput.value;
    const rol = roleSelect.value;
    const idPlantel = plantelSelect.value ? Number(plantelSelect.value) : null;
    const usuarios = mockData.readUsuarios();

    const validName = nombre.length > 0;
    const validLastName = apellido.length > 0;
    const validEmailFormat = /.+@.+\..+/.test(correo);
    const uniqueEmail = !usuarios.some((usuario) => String(usuario.correo).toLocaleLowerCase('es') === correo);
    const validEmail = validEmailFormat && uniqueEmail;
    const validPassword = password.length >= 8;
    const validConfirmation = validPassword && confirmInput.value === password;
    const validRole = Object.hasOwn(roleLabels, rol);
    const validPlantel = rol !== 'ADMIN_PLANTEL' || planteles.some((plantel) => Number(plantel.id) === idPlantel);

    const emailError = document.getElementById('userEmailError');
    if (emailError) emailError.textContent = validEmailFormat ? 'Ya existe un usuario con este correo.' : 'Ingresa un correo válido.';
    toggleError(nameInput, 'userNameError', validName);
    toggleError(lastNameInput, 'userLastNameError', validLastName);
    toggleError(emailInput, 'userEmailError', validEmail, '.form-input-icon');
    toggleError(passwordInput, 'userPasswordError', validPassword, '.form-input-icon');
    toggleError(confirmInput, 'userPasswordConfirmError', validConfirmation, '.form-input-icon');
    toggleError(roleSelect, 'userRoleError', validRole, '.form-select');
    toggleError(plantelSelect, 'userPlantelError', validPlantel, '.form-select');

    if (!validName || !validLastName || !validEmail || !validPassword || !validConfirmation || !validRole || !validPlantel) return;

    usuarios.push({
      id: mockData.nextUsuarioId(usuarios),
      nombre,
      apellido,
      correo,
      rol,
      idPlantel,
      activo: true,
    });
    mockData.writeUsuarios(usuarios);
    window.location.assign(form.dataset.listUrl || '/admin/usuarios');
  });

  updatePreview();
});
