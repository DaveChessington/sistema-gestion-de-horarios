document.addEventListener('DOMContentLoaded', () => {
  const sessionKey = 'schedule.mockSession';
  const loginUrl = document.body.dataset.loginUrl || '/login';
  const rawSession = window.sessionStorage.getItem(sessionKey);

  if (!rawSession) {
    window.location.replace(loginUrl);
    return;
  }

  try {
    const session = JSON.parse(rawSession);
    const name = document.getElementById('mockSessionName');
    const role = document.getElementById('mockSessionRole');
    if (name) name.textContent = session.name || 'Usuario demo';
    if (role) role.textContent = session.role || 'ROL DEMO';
  } catch (error) {
    window.sessionStorage.removeItem(sessionKey);
    window.location.replace(loginUrl);
    return;
  }

  document.getElementById('mockLogout')?.addEventListener('click', () => {
    window.sessionStorage.removeItem(sessionKey);
    window.location.assign(loginUrl);
  });
});
