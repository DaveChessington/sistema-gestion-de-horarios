document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('loginForm');
  const correoInput = document.getElementById('correo');
  const passwordInput = document.getElementById('password');
  const correoError = document.getElementById('correoError');
  const passwordError = document.getElementById('passwordError');
  const submitButton = form?.querySelector('button[type="submit"]');
  const submitLabel = document.getElementById('submitLabel');
  const submitIcon = document.getElementById('submitIcon');
  const togglePassword = document.getElementById('togglePassword');
  const credentialError = document.getElementById('loginCredentialError');

  if (!form || !correoInput || !passwordInput) return;

  const setError = (input, errorElement, isValid) => {
    input.classList.toggle('field-error', !isValid);
    errorElement?.classList.toggle('hidden', isValid);
    input.setAttribute('aria-invalid', String(!isValid));
  };

  const validate = () => {
    const correo = correoInput.value.trim();
    const password = passwordInput.value.trim();
    const isCorreoValid = /.+@.+\..+/.test(correo);
    const isPasswordValid = password.length > 0;

    setError(correoInput, correoError, isCorreoValid);
    setError(passwordInput, passwordError, isPasswordValid);
    return isCorreoValid && isPasswordValid;
  };

  correoInput.addEventListener('input', validate);
  passwordInput.addEventListener('input', validate);

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!validate()) return;

    const credentialsAreValid = correoInput.value.trim().toLowerCase() === 'admin@udl.edu.mx'
      && passwordInput.value === 'demo1234';
    credentialError?.classList.toggle('hidden', credentialsAreValid);
    if (!credentialsAreValid) return;

    form.classList.add('is-loading');
    submitButton?.setAttribute('disabled', 'true');
    if (submitLabel) submitLabel.textContent = 'Validando...';
    if (submitIcon) submitIcon.className = 'fa-solid fa-spinner fa-spin ml-2';

    window.sessionStorage.setItem('schedule.mockSession', JSON.stringify({
      name: 'Administrador Demo',
      email: correoInput.value.trim().toLowerCase(),
      role: 'COORDINADOR',
    }));

    window.setTimeout(() => {
      window.location.assign(form.dataset.adminUrl || '/admin');
    }, 500);
  });

  togglePassword?.addEventListener('click', () => {
    const showPassword = passwordInput.type === 'password';
    passwordInput.type = showPassword ? 'text' : 'password';
    togglePassword.innerHTML = showPassword
      ? '<i class="fa-solid fa-eye-slash"></i>'
      : '<i class="fa-solid fa-eye"></i>';
    togglePassword.setAttribute(
      'aria-label',
      showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña',
    );
  });
});
