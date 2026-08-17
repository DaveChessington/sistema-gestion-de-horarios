document.addEventListener('DOMContentLoaded', () => {
  const roleNotice = document.getElementById('rolePermissionNotice');
  const roleNoticeClose = document.getElementById('rolePermissionNoticeClose');
  roleNoticeClose?.addEventListener('click', () => roleNotice?.remove());

  const scheduleView = document.body.dataset.scheduleView;
  const scheduleBody = document.querySelector('[data-schedule-body]');
  const mobileSchedule = document.querySelector('[data-schedule-mobile]');
  const periodButtons = [...document.querySelectorAll('[data-period-target]')];
  const filterForm = document.querySelector('[data-schedule-filters]');
  const filterSubmit = filterForm?.querySelector('[data-filter-submit]');
  const filterStatus = filterForm?.querySelector('[data-schedule-filter-status]');
  const scheduleError = document.querySelector('[data-schedule-error]');
  const scheduleErrorMessage = document.querySelector('[data-schedule-error-message]');
  const schedulePanels = [...document.querySelectorAll('[data-schedule-panel], [data-schedule-mobile]')];

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

  const bookingDataElement = document.getElementById('bookingScheduleData');
  let bookingRecords = [];
  if (bookingDataElement) {
    try {
      const parsedRecords = JSON.parse(bookingDataElement.textContent || '[]');
      bookingRecords = Array.isArray(parsedRecords) ? parsedRecords : [];
    } catch {
      bookingRecords = [];
    }
  }
  let activePeriod = 'morning';
  let filterOptions = { planteles: [], salones: [], programas: [] };

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const timeToMinutes = (value) => {
    const [hours, minutes] = String(value || '').split(':').map(Number);
    if (!Number.isInteger(hours) || !Number.isInteger(minutes)) return null;
    return (hours * 60) + minutes;
  };

  const bookingMatches = (day, start, end) => {
    const dayIndex = days.indexOf(day) + 1;
    const slotStart = timeToMinutes(start);
    const slotEnd = timeToMinutes(end);
    if (dayIndex < 1 || slotStart === null || slotEnd === null) return [];

    return bookingRecords.filter((record) => {
      const recordDate = new Date(`${record.fecha_reserva}T12:00:00`);
      const recordStart = timeToMinutes(record.hora_inicio);
      const recordEnd = timeToMinutes(record.hora_fin);
      return !Number.isNaN(recordDate.getTime())
        && recordDate.getDay() === dayIndex
        && recordStart !== null
        && recordEnd !== null
        && recordStart < slotEnd
        && recordEnd > slotStart;
    });
  };

  const bookingSample = (day, start, end) => {
    const matches = bookingMatches(day, start, end);
    if (matches.length === 0) return null;
    if (matches.length > 1) {
      return ['assigned', `${matches.length} reservas`, 'Espacios ocupados', 'Consulta por salón', 'Booking'];
    }

    const record = matches[0];
    return [
      'assigned',
      record.nombre_tipo_evento || record.estado || 'Reserva',
      record.materia_nombre || 'Reserva académica',
      `Salón ${record.id_salon}`,
      record.estado || 'APROBADA'
    ];
  };

  const sampleFor = (_period, day, start, end) => bookingSample(day, start, end);

  const publicSlot = (sample, start, end) => {
    if (!sample) return `<article class="schedule-slot schedule-free"><i class="fa-regular fa-circle-check"></i><strong>Disponible</strong><span>${start} – ${end}</span></article>`;
    const [status, group, title, room, detail] = sample.map(escapeHtml);
    if (status === 'maintenance') return `<article class="schedule-slot schedule-maintenance"><i class="fa-solid fa-screwdriver-wrench"></i><strong>${title}</strong><span>${room}</span></article>`;
    if (status === 'conflict') return `<article class="schedule-slot schedule-occupied"><div class="schedule-slot-top"><span>${group}</span><i class="fa-solid fa-triangle-exclamation"></i></div><h3>${title}</h3><p>${room}</p><small>Requiere revisión</small></article>`;
    return `<article class="schedule-slot schedule-occupied"><div class="schedule-slot-top"><span>${group}</span><i class="fa-solid fa-lock"></i></div><h3>${title}</h3><p>${room}</p><small>${detail || 'Reserva confirmada'}</small></article>`;
  };

  const adminSlot = (sample) => {
    if (!sample) return '<article class="admin-schedule-slot slot-free"><i class="fa-regular fa-circle-check"></i><span>Bloque libre</span></article>';
    const [status, group, title, room, detail] = sample.map(escapeHtml);
    if (status === 'maintenance') return `<article class="admin-schedule-slot slot-maintenance"><i class="fa-solid fa-screwdriver-wrench"></i><span>${title} · ${room}</span></article>`;
    if (status === 'conflict') return `<article class="admin-schedule-slot slot-conflict"><div><span>${group}</span><i class="fa-solid fa-triangle-exclamation"></i></div><h4>${title}</h4><p>${room}</p></article>`;
    return `<article class="admin-schedule-slot slot-assigned"><div><span>${group}</span><i class="fa-solid fa-lock"></i></div><h4>${title}</h4><p>${room} · ${detail || 'Reserva confirmada'}</p></article>`;
  };

  const renderTable = (period) => {
    scheduleBody.innerHTML = periods[period].map(([start, end]) => `
      <tr>
        <th class="${scheduleView === 'admin' ? 'admin-schedule-time' : 'schedule-time'}">${start}<span>${end}</span></th>
        ${days.map(day => `<td>${scheduleView === 'admin' ? adminSlot(sampleFor(period, day, start, end)) : publicSlot(sampleFor(period, day, start, end), start, end)}</td>`).join('')}
      </tr>
    `).join('');
  };

  const mobileItem = (sample, start, end) => {
    const status = sample?.[0] || 'free';
    const title = escapeHtml(sample?.[2] || 'Bloque libre');
    const detail = sample
      ? `${sample[1] ? `${escapeHtml(sample[1])} · ` : ''}${escapeHtml(sample[3])}`
      : 'Disponible para asignación';
    const colors = { assigned: 'bg-blue-400', conflict: 'bg-red-500', maintenance: 'bg-amber-400', free: 'bg-emerald-400' };
    const textColor = status === 'conflict' ? 'text-red-700' : status === 'free' ? 'text-emerald-700' : '';
    return `<div class="mobile-schedule-item"><time>${start}<br><span>${end}</span></time><div class="mobile-status-line ${colors[status]}"></div><div class="min-w-0 flex-1"><p class="truncate text-sm font-semibold ${textColor}">${title}</p><p class="mt-1 text-xs text-slate-500">${detail}</p></div></div>`;
  };

  const renderMobile = (period) => {
    const mobileDays = days;
    mobileSchedule.innerHTML = mobileDays.map(day => {
      const items = periods[period].map(([start, end]) => mobileItem(sampleFor(period, day, start, end), start, end)).join('');
      return `<article class="public-day-card"><div class="public-day-header"><div><p class="text-[10px] font-bold uppercase tracking-[0.15em] text-blue-600">${period === 'morning' ? 'Turno Matutino' : 'Turno Vespertino'}</p><h3 class="mt-1 font-semibold">${day}</h3></div><span>${periods[period].length} bloques</span></div><div class="divide-y divide-slate-100">${items}</div></article>`;
    }).join('');
  };

  const selectPeriod = (period) => {
    activePeriod = period;
    periodButtons.forEach(button => {
      const active = button.dataset.periodTarget === period;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', String(active));
    });
    renderTable(period);
    renderMobile(period);
  };

  const setScheduleError = (message = '') => {
    const hasError = Boolean(message);
    scheduleError?.classList.toggle('hidden', !hasError);
    if (scheduleErrorMessage) scheduleErrorMessage.textContent = message;
    schedulePanels.forEach(panel => panel.classList.toggle('invisible', hasError));
  };

  const updateMetrics = () => {
    if (scheduleView !== 'admin') return;
    const metrics = {
      total: bookingRecords.length,
      rooms: new Set(bookingRecords.map(record => record.id_salon).filter(Boolean)).size,
      morning: bookingRecords.filter(record => {
        const hour = Number.parseInt(String(record.hora_inicio || '').split(':')[0], 10);
        return hour >= 7 && hour <= 13;
      }).length,
      afternoon: bookingRecords.filter(record => {
        const hour = Number.parseInt(String(record.hora_inicio || '').split(':')[0], 10);
        return hour >= 16 && hour <= 21;
      }).length
    };
    Object.entries(metrics).forEach(([name, value]) => {
      document.querySelectorAll(`[data-schedule-metric="${name}"]`).forEach(element => {
        element.textContent = String(value);
      });
    });
  };

  const optionId = (record, names) => {
    const name = names.find(key => record[key] !== undefined && record[key] !== null);
    return name ? String(record[name]) : '';
  };

  const fillSelect = (select, records, idNames, labelNames, placeholder, selectedValue = '') => {
    if (!select) return;
    const options = records.map(record => {
      const value = optionId(record, idNames);
      const labelKey = labelNames.find(key => record[key]);
      const label = labelKey ? record[labelKey] : `Registro ${value}`;
      return `<option value="${escapeHtml(value)}"${value === String(selectedValue) ? ' selected' : ''}>${escapeHtml(label)}</option>`;
    }).join('');
    select.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>${options}`;
  };

  const selectedFilterValue = (name) => {
    const control = filterForm?.elements.namedItem(name);
    if (control?.value) return control.value;
    return new URLSearchParams(window.location.search).get(name) || '';
  };

  const refreshSalonOptions = () => {
    const plantelSelect = filterForm?.querySelector('[data-filter-plantel]');
    const salonSelect = filterForm?.querySelector('[data-filter-salon]');
    const selectedSalon = selectedFilterValue('id_salon');
    const plantelId = plantelSelect?.value || '';
    const salones = plantelId
      ? filterOptions.salones.filter(record => String(record.id_plantel) === String(plantelId))
      : filterOptions.salones;
    fillSelect(salonSelect, salones, ['id_salon', 'id'], ['numero', 'nombre'], 'Todos los salones', selectedSalon);
  };

  const loadFilterOptions = async () => {
    const url = filterForm?.dataset.filterOptionsUrl;
    if (!url) return;
    try {
      const response = await fetch(url, { headers: { Accept: 'application/json' } });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'No fue posible obtener los filtros.');
      filterOptions = {
        planteles: Array.isArray(payload.planteles) ? payload.planteles : [],
        salones: Array.isArray(payload.salones) ? payload.salones : [],
        programas: Array.isArray(payload.programas) ? payload.programas : []
      };
      fillSelect(
        filterForm.querySelector('[data-filter-plantel]'),
        filterOptions.planteles,
        ['id', 'id_plantel'],
        ['nombre'],
        'Todos los planteles',
        selectedFilterValue('id_plantel')
      );
      fillSelect(
        filterForm.querySelector('[data-filter-programa]'),
        filterOptions.programas,
        ['id_programa', 'id'],
        ['nombre'],
        'Todos los programas',
        selectedFilterValue('id_programa')
      );
      refreshSalonOptions();
    } catch (error) {
      if (filterStatus) {
        filterStatus.textContent = error.message;
        filterStatus.classList.remove('hidden');
      }
    }
  };

  const updateSummary = () => {
    const summary = document.querySelector('[data-schedule-summary]');
    if (!summary || !filterForm) return;
    const plantel = filterForm.querySelector('[data-filter-plantel]')?.selectedOptions?.[0]?.textContent || 'Todos los planteles';
    const salon = filterForm.querySelector('[data-filter-salon]')?.selectedOptions?.[0]?.textContent || 'Todos los salones';
    summary.textContent = `${plantel} · ${salon}`;
  };

  const submitFilters = async () => {
    const apiUrl = filterForm?.dataset.scheduleApiUrl;
    if (!apiUrl || !filterForm) return;
    const query = new URLSearchParams();
    new FormData(filterForm).forEach((value, name) => {
      if (String(value).trim()) query.set(name, String(value).trim());
    });
    filterSubmit?.setAttribute('disabled', 'disabled');
    if (filterStatus) {
      filterStatus.textContent = 'Consultando horarios…';
      filterStatus.classList.remove('hidden');
    }
    try {
      const response = await fetch(`${apiUrl}${query.size ? `?${query}` : ''}`, {
        headers: { Accept: 'application/json' }
      });
      const payload = await response.json();
      if (!response.ok || !Array.isArray(payload.grid)) {
        throw new Error(payload.error || 'La respuesta de horarios no es válida.');
      }
      bookingRecords = payload.grid;
      setScheduleError();
      updateMetrics();
      updateSummary();
      selectPeriod(activePeriod);
      window.history.replaceState({}, '', `${window.location.pathname}${query.size ? `?${query}` : ''}`);
      if (filterStatus) filterStatus.textContent = `${bookingRecords.length} reservas encontradas.`;
    } catch (error) {
      setScheduleError(error.message);
      if (filterStatus) filterStatus.textContent = 'No fue posible actualizar la consulta.';
    } finally {
      filterSubmit?.removeAttribute('disabled');
    }
  };

  periodButtons.forEach(button => button.addEventListener('click', () => selectPeriod(button.dataset.periodTarget)));
  filterForm?.querySelector('[data-filter-plantel]')?.addEventListener('change', refreshSalonOptions);
  filterForm?.addEventListener('submit', (event) => {
    event.preventDefault();
    submitFilters();
  });
  filterForm?.addEventListener('reset', () => {
    window.setTimeout(() => {
      refreshSalonOptions();
      submitFilters();
    }, 0);
  });
  selectPeriod('morning');
  updateMetrics();
  loadFilterOptions().then(updateSummary);
});
