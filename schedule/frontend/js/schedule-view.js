document.addEventListener('DOMContentLoaded', () => {
  const scheduleView = document.body.dataset.scheduleView;
  const scheduleBody = document.querySelector('[data-schedule-body]');
  const mobileSchedule = document.querySelector('[data-schedule-mobile]');
  const periodButtons = [...document.querySelectorAll('[data-period-target]')];

  if (!scheduleView || !scheduleBody || !mobileSchedule || periodButtons.length === 0) return;

  const periods = {
    morning: [
      ['7:00', '7:50'], ['8:00', '8:50'], ['9:00', '9:50'], ['10:00', '10:50'],
      ['11:00', '11:50'], ['12:00', '12:50'], ['13:00', '13:50']
    ],
    afternoon: [
      ['16:00', '16:50'], ['17:00', '17:50'], ['18:00', '18:50'],
      ['19:00', '19:50'], ['20:00', '20:50'], ['21:00', '21:50']
    ]
  };

  const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'];

  const samples = {
    morning: {
      '7:00-Lunes': ['assigned', 'ICO 901', 'Sistemas Operativos', 'Laboratorio 01'],
      '8:00-Miércoles': ['assigned', 'ICO 401', 'Estructuras de Datos', 'Laboratorio 02'],
      '9:00-Martes': ['conflict', 'Conflicto', 'Dos asignaciones', 'Laboratorio 02'],
      '10:00-Jueves': ['assigned', 'ICO 602', 'Bases de Datos', 'Laboratorio 01'],
      '11:00-Lunes': ['assigned', 'ICO 701', 'Ingeniería de Software', 'Laboratorio 03'],
      '12:00-Jueves': ['maintenance', '', 'Mantenimiento', 'Laboratorio 03'],
      '13:00-Viernes': ['assigned', 'IIA 801', 'Inteligencia Artificial', 'Laboratorio 02']
    },
    afternoon: {
      '16:00-Lunes': ['assigned', 'ICO 501', 'Programación Web', 'Laboratorio 01'],
      '17:00-Martes': ['assigned', 'IIA 701', 'Aprendizaje Automático', 'Laboratorio 03'],
      '18:00-Miércoles': ['assigned', 'ICO 801', 'Seguridad Informática', 'Laboratorio 02'],
      '19:00-Jueves': ['conflict', 'Conflicto', 'Cruce de grupos', 'Laboratorio 01'],
      '20:00-Viernes': ['maintenance', '', 'Mantenimiento', 'Laboratorio 03'],
      '21:00-Lunes': ['assigned', 'ICO 901', 'Proyecto Integrador', 'Laboratorio 02']
    }
  };

  const publicSlot = (sample, start, end) => {
    if (!sample) return `<article class="schedule-slot schedule-free"><i class="fa-regular fa-circle-check"></i><strong>Disponible</strong><span>${start} – ${end}</span></article>`;
    const [status, group, title, room] = sample;
    if (status === 'maintenance') return `<article class="schedule-slot schedule-maintenance"><i class="fa-solid fa-screwdriver-wrench"></i><strong>${title}</strong><span>${room}</span></article>`;
    if (status === 'conflict') return `<article class="schedule-slot schedule-occupied"><div class="schedule-slot-top"><span>${group}</span><i class="fa-solid fa-triangle-exclamation"></i></div><h3>${title}</h3><p>${room}</p><small>Requiere revisión</small></article>`;
    return `<article class="schedule-slot schedule-occupied"><div class="schedule-slot-top"><span>${group}</span><i class="fa-solid fa-lock"></i></div><h3>${title}</h3><p>${room}</p><small>Docente de muestra</small></article>`;
  };

  const adminSlot = (sample) => {
    if (!sample) return '<article class="admin-schedule-slot slot-free"><i class="fa-solid fa-plus"></i><span>Bloque libre</span></article>';
    const [status, group, title, room] = sample;
    if (status === 'maintenance') return `<article class="admin-schedule-slot slot-maintenance"><i class="fa-solid fa-screwdriver-wrench"></i><span>${title} · ${room}</span></article>`;
    if (status === 'conflict') return `<article class="admin-schedule-slot slot-conflict"><div><span>${group}</span><i class="fa-solid fa-triangle-exclamation"></i></div><h4>${title}</h4><p>${room}</p></article>`;
    return `<article class="admin-schedule-slot slot-assigned"><div><span>${group}</span><i class="fa-regular fa-pen-to-square"></i></div><h4>${title}</h4><p>${room} · Docente de muestra</p></article>`;
  };

  const renderTable = (period) => {
    scheduleBody.innerHTML = periods[period].map(([start, end]) => `
      <tr>
        <th class="${scheduleView === 'admin' ? 'admin-schedule-time' : 'schedule-time'}">${start}<span>${end}</span></th>
        ${days.map(day => `<td>${scheduleView === 'admin' ? adminSlot(samples[period][`${start}-${day}`]) : publicSlot(samples[period][`${start}-${day}`], start, end)}</td>`).join('')}
      </tr>
    `).join('');
  };

  const mobileItem = (sample, start, end) => {
    const status = sample?.[0] || 'free';
    const title = sample?.[2] || 'Bloque libre';
    const detail = sample ? `${sample[1] ? `${sample[1]} · ` : ''}${sample[3]}` : 'Disponible para asignación';
    const colors = { assigned: 'bg-blue-400', conflict: 'bg-red-500', maintenance: 'bg-amber-400', free: 'bg-emerald-400' };
    const textColor = status === 'conflict' ? 'text-red-700' : status === 'free' ? 'text-emerald-700' : '';
    return `<div class="mobile-schedule-item"><time>${start}<br><span>${end}</span></time><div class="mobile-status-line ${colors[status]}"></div><div class="min-w-0 flex-1"><p class="truncate text-sm font-semibold ${textColor}">${title}</p><p class="mt-1 text-xs text-slate-500">${detail}</p></div></div>`;
  };

  const renderMobile = (period) => {
    mobileSchedule.innerHTML = ['Lunes', 'Martes'].map(day => {
      const items = periods[period].map(([start, end]) => mobileItem(samples[period][`${start}-${day}`], start, end)).join('');
      return `<article class="public-day-card"><div class="public-day-header"><div><p class="text-[10px] font-bold uppercase tracking-[0.15em] text-blue-600">${period === 'morning' ? 'Turno Matutino' : 'Turno Vespertino'}</p><h3 class="mt-1 font-semibold">${day}</h3></div><span>${periods[period].length} bloques</span></div><div class="divide-y divide-slate-100">${items}</div></article>`;
    }).join('');
  };

  const selectPeriod = (period) => {
    periodButtons.forEach(button => {
      const active = button.dataset.periodTarget === period;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', String(active));
    });
    renderTable(period);
    renderMobile(period);
  };

  periodButtons.forEach(button => button.addEventListener('click', () => selectPeriod(button.dataset.periodTarget)));
  selectPeriod('morning');
});
