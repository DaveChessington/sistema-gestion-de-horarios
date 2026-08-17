document.addEventListener('DOMContentLoaded', () => {
  const historyDataElement = document.getElementById('bookingHistoryData');
  const salonDataElement = document.getElementById('historySalonData');
  const plantelDataElement = document.getElementById('historyPlantelData');
  const configDataElement = document.getElementById('historyConfigData');
  const searchInput = document.getElementById('historySearch');
  const tableBody = document.getElementById('historyTableBody');
  const mobileGrid = document.getElementById('historyMobileGrid');
  const resultCount = document.getElementById('historyResultCount');
  const previousButton = document.getElementById('historyPreviousPage');
  const nextButton = document.getElementById('historyNextPage');
  const currentPageButton = document.getElementById('historyCurrentPage');

  if (!historyDataElement || !tableBody || !mobileGrid) return;

  let records = [];
  let salons = [];
  let planteles = [];
  let cancelUrlTemplate = '';
  let editUrlTemplate = '';
  try {
    const parsedRecords = JSON.parse(historyDataElement.textContent || '[]');
    const parsedSalons = JSON.parse(salonDataElement?.textContent || '[]');
    const parsedPlanteles = JSON.parse(plantelDataElement?.textContent || '[]');
    const parsedConfig = JSON.parse(configDataElement?.textContent || '{}');
    records = Array.isArray(parsedRecords) ? parsedRecords : [];
    salons = Array.isArray(parsedSalons) ? parsedSalons : [];
    planteles = Array.isArray(parsedPlanteles) ? parsedPlanteles : [];
    cancelUrlTemplate = typeof parsedConfig.cancel_url_template === 'string'
      ? parsedConfig.cancel_url_template
      : '';
    editUrlTemplate = typeof parsedConfig.edit_url_template === 'string'
      ? parsedConfig.edit_url_template
      : '';
  } catch {
    records = [];
    salons = [];
    planteles = [];
    cancelUrlTemplate = '';
    editUrlTemplate = '';
  }

  const pageSize = 6;
  let currentPage = 1;
  const statusVisuals = {
    APROBADA: { label: 'Aprobada', className: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-400' },
    APARTADA: { label: 'Apartada', className: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-400' },
    PENDIENTE: { label: 'Pendiente', className: 'bg-blue-50 text-blue-700', dot: 'bg-blue-400' },
    RECHAZADA: { label: 'Rechazada', className: 'bg-red-50 text-red-700', dot: 'bg-red-400' },
    DESPLAZADA: { label: 'Desplazada', className: 'bg-amber-50 text-amber-700', dot: 'bg-amber-400' },
    CANCELADA: { label: 'Cancelada', className: 'bg-slate-100 text-slate-600', dot: 'bg-slate-400' },
  };
  const cancellableStates = new Set(['APROBADA', 'APARTADA', 'PENDIENTE']);

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const salonFor = (record) => salons.find(salon => Number(salon.id_salon) === Number(record.id_salon));
  const plantelFor = (salon) => planteles.find(plantel => Number(plantel.id) === Number(salon?.id_plantel));
  const timeLabel = (value) => String(value || '').slice(0, 5) || '—';
  const dateLabel = (value) => {
    const parsed = new Date(`${value || ''}T00:00:00Z`);
    return Number.isNaN(parsed.getTime())
      ? 'Fecha no disponible'
      : new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeZone: 'UTC' }).format(parsed);
  };
  const statusFor = (record) => statusVisuals[record.estado] || {
    label: record.estado || 'Sin estado', className: 'bg-slate-100 text-slate-600', dot: 'bg-slate-400'
  };
  const statusBadge = (record) => {
    const status = statusFor(record);
    return `<span class="inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-[11px] font-bold ${status.className}"><span class="h-1.5 w-1.5 rounded-full ${status.dot}"></span>${escapeHtml(status.label)}</span>`;
  };
  const cancelAction = (record, mobile = false) => {
    const bookingId = Number(record.id_peticion);
    if (
      !cancellableStates.has(record.estado)
      || !Number.isInteger(bookingId)
      || bookingId <= 0
      || !cancelUrlTemplate
    ) return mobile ? '' : '<span class="text-xs text-slate-300">—</span>';

    const action = cancelUrlTemplate.replace(/\/0\/cancelar$/, `/${bookingId}/cancelar`)
      + window.location.search;
    const label = `Cancelar solicitud #${bookingId}`;
    return `
      <form method="post" action="${escapeHtml(action)}" data-cancel-booking-form data-booking-id="${bookingId}"${mobile ? ' class="mt-4"' : ''}>
        <button type="submit" class="${mobile ? 'inline-flex w-full items-center justify-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs font-semibold text-red-700' : 'table-action table-action-danger'}" aria-label="${escapeHtml(label)}">
          <i class="fa-regular fa-calendar-xmark"></i>${mobile ? '<span>Cancelar reserva</span>' : ''}
        </button>
      </form>`;
  };

  const editAction = (record, mobile = false) => {
    const bookingId = Number(record.id_peticion);
    if (!cancellableStates.has(record.estado) || !Number.isInteger(bookingId) || bookingId <= 0 || !editUrlTemplate) {
      return '';
    }
    const href = editUrlTemplate.replace(/\/0\/editar$/, `/${bookingId}/editar`);
    return `<a href="${escapeHtml(href)}" class="${mobile ? 'inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2.5 text-xs font-semibold text-blue-700' : 'table-action'}" aria-label="Editar solicitud #${bookingId}"><i class="fa-regular fa-pen-to-square"></i>${mobile ? '<span>Editar reserva</span>' : ''}</a>`;
  };

  const searchableRecords = () => {
    const query = searchInput?.value.trim().toLocaleLowerCase('es') || '';
    return records.filter((record) => {
      const salon = salonFor(record);
      const plantel = plantelFor(salon);
      const searchable = [
        record.id_peticion, record.materia_nombre, record.nombre_tipo_evento,
        record.estado, record.id_usuario, salon?.numero, plantel?.nombre
      ].join(' ').toLocaleLowerCase('es');
      return searchable.includes(query);
    });
  };

  const tableRow = (record) => {
    const salon = salonFor(record);
    const plantel = plantelFor(salon);
    const reason = record.motivo_rechazo
      ? `<p class="mt-1 max-w-xs truncate text-[11px] text-red-500" title="${escapeHtml(record.motivo_rechazo)}">${escapeHtml(record.motivo_rechazo)}</p>`
      : '';
    return `
      <tr class="catalog-row">
        <td class="px-6 py-4"><p class="text-sm font-semibold">#${escapeHtml(record.id_peticion)}</p><p class="mt-1 text-xs text-slate-400">${escapeHtml(record.nombre_tipo_evento || 'Reserva')}</p></td>
        <td class="px-6 py-4"><p class="text-sm font-semibold text-slate-700">${escapeHtml(record.materia_nombre || 'Actividad sin nombre')}</p>${reason}</td>
        <td class="px-6 py-4"><p class="text-sm font-medium text-slate-700">${escapeHtml(salon?.numero || `Salón ${record.id_salon}`)}</p><p class="mt-1 text-xs text-slate-400">${escapeHtml(plantel?.nombre || 'Plantel no disponible')}</p></td>
        <td class="px-6 py-4"><p class="text-sm font-medium text-slate-700">${escapeHtml(dateLabel(record.fecha_reserva || record.fecha))}</p><p class="mt-1 text-xs text-slate-400">${escapeHtml(timeLabel(record.hora_inicio))} – ${escapeHtml(timeLabel(record.hora_fin))}</p></td>
        <td class="px-6 py-4"><p class="text-sm font-medium text-slate-700">Usuario #${escapeHtml(record.id_usuario)}</p><p class="mt-1 text-xs text-slate-400">Prioridad ${escapeHtml(record.prioridad_calculada ?? 0)}</p></td>
        <td class="px-6 py-4">${statusBadge(record)}</td>
        <td class="px-6 py-4"><div class="flex justify-end gap-2">${editAction(record)}${cancelAction(record)}</div></td>
      </tr>`;
  };

  const mobileCard = (record) => {
    const salon = salonFor(record);
    const plantel = plantelFor(salon);
    return `
      <article class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div class="flex items-start justify-between gap-3"><div><p class="text-xs font-bold uppercase tracking-wide text-blue-600">Solicitud #${escapeHtml(record.id_peticion)}</p><h3 class="mt-2 text-sm font-semibold">${escapeHtml(record.materia_nombre || 'Actividad sin nombre')}</h3><p class="mt-1 text-xs text-slate-400">${escapeHtml(record.nombre_tipo_evento || 'Reserva')}</p></div>${statusBadge(record)}</div>
        <div class="mt-4 grid gap-3 border-t border-slate-100 pt-4 text-xs sm:grid-cols-2"><div><p class="text-slate-400">Espacio</p><p class="mt-1 font-semibold text-slate-700">${escapeHtml(salon?.numero || `Salón ${record.id_salon}`)}</p><p class="mt-1 text-slate-400">${escapeHtml(plantel?.nombre || 'Plantel no disponible')}</p></div><div><p class="text-slate-400">Fecha y bloque</p><p class="mt-1 font-semibold text-slate-700">${escapeHtml(dateLabel(record.fecha_reserva || record.fecha))}</p><p class="mt-1 text-slate-400">${escapeHtml(timeLabel(record.hora_inicio))} – ${escapeHtml(timeLabel(record.hora_fin))}</p></div></div>
        <div class="mt-4 flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-xs"><span class="text-slate-500">Usuario #${escapeHtml(record.id_usuario)}</span><strong class="text-slate-700">Prioridad ${escapeHtml(record.prioridad_calculada ?? 0)}</strong></div>
        <div class="mt-4 flex gap-2">${editAction(record, true)}${cancelAction(record, true)}</div>
      </article>`;
  };

  const render = () => {
    const filtered = searchableRecords();
    const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
    currentPage = Math.min(currentPage, pageCount);
    const visible = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);
    tableBody.innerHTML = visible.length
      ? visible.map(tableRow).join('')
      : '<tr><td colspan="7" class="px-6 py-12 text-center text-sm text-slate-400">No se encontraron solicitudes.</td></tr>';
    mobileGrid.innerHTML = visible.length
      ? visible.map(mobileCard).join('')
      : '<p class="py-10 text-center text-sm text-slate-400">No se encontraron solicitudes.</p>';
    if (resultCount) resultCount.innerHTML = `Mostrando <strong class="text-slate-700">${visible.length} de ${filtered.length}</strong> solicitudes`;
    if (currentPageButton) currentPageButton.textContent = String(currentPage);
    if (previousButton) previousButton.disabled = currentPage <= 1;
    if (nextButton) nextButton.disabled = currentPage >= pageCount;
  };

  searchInput?.addEventListener('input', () => { currentPage = 1; render(); });
  previousButton?.addEventListener('click', () => { currentPage -= 1; render(); });
  nextButton?.addEventListener('click', () => { currentPage += 1; render(); });
  document.addEventListener('submit', (event) => {
    const form = event.target.closest('[data-cancel-booking-form]');
    if (!form) return;
    const bookingId = form.dataset.bookingId;
    const confirmed = window.confirm(
      `¿Confirmas que deseas cancelar la solicitud #${bookingId}? Esta acción liberará el bloque reservado.`
    );
    if (!confirmed) {
      event.preventDefault();
      return;
    }
    const button = form.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
    }
  });
  render();
});
