(function initializeScheduleMockData() {
  const plantelesKey = 'schedule.mockPlanteles';
  const salonesKey = 'schedule.mockSalones';
  const programasKey = 'schedule.mockProgramas';
  const equiposKey = 'schedule.mockEquipos';
  const usuariosKey = 'schedule.mockUsuarios';
  const defaultPlanteles = [
    { id: 1, nombre: 'Plantel León', direccion: 'León, Guanajuato', activo: true },
    { id: 2, nombre: 'Plantel Centro', direccion: 'Zona Centro, Guanajuato', activo: true },
    { id: 3, nombre: 'Plantel Norte', direccion: 'Zona Norte, Guanajuato', activo: false },
  ];
  const defaultSalones = [
    { id: 101, numero: 'Laboratorio 01', descripcion: 'Laboratorio de cómputo general', capacidad: 30, idPlantel: 1, activo: true },
    { id: 102, numero: 'Laboratorio 02', descripcion: 'Redes y telecomunicaciones', capacidad: 25, idPlantel: 1, activo: true },
    { id: 103, numero: 'Laboratorio 03', descripcion: 'Cómputo especializado', capacidad: 35, idPlantel: 2, activo: false },
    { id: 104, numero: 'Aula multimedia', descripcion: 'Presentaciones y videoconferencias', capacidad: 30, idPlantel: 2, activo: true },
  ];
  const defaultProgramas = [
    { id: 201, nombre: 'Visual Studio Code', descripcion: 'Editor para desarrollo y prácticas de programación.', activo: true, equiposAsociados: 8, icono: 'fa-solid fa-code', color: 'bg-blue-600' },
    { id: 202, nombre: 'Python', descripcion: 'Entorno para prácticas de programación y análisis de datos.', activo: true, equiposAsociados: 6, icono: 'fa-brands fa-python', color: 'bg-sky-500' },
    { id: 203, nombre: 'PostgreSQL', descripcion: 'Gestor de bases de datos para laboratorios académicos.', activo: true, equiposAsociados: 4, icono: 'fa-solid fa-database', color: 'bg-indigo-600' },
    { id: 204, nombre: 'Docker Desktop', descripcion: 'Plataforma de contenedores para entornos de desarrollo.', activo: false, equiposAsociados: 0, icono: 'fa-brands fa-docker', color: 'bg-slate-800' },
    { id: 205, nombre: 'Git', descripcion: 'Control de versiones para proyectos y prácticas colaborativas.', activo: true, equiposAsociados: 0, icono: 'fa-brands fa-git-alt', color: 'bg-orange-600' },
    { id: 206, nombre: 'Node.js', descripcion: 'Entorno de ejecución para desarrollo web del lado del servidor.', activo: true, equiposAsociados: 0, icono: 'fa-brands fa-node-js', color: 'bg-emerald-600' },
  ];
  const defaultEquipos = [
    { id: 301, numero: 'PC-001', descripcion: 'Estación de trabajo', idSalon: 101, activo: true, programas: [201, 203, 205, 206] },
    { id: 302, numero: 'PC-002', descripcion: 'Estación de trabajo', idSalon: 101, activo: true, programas: [202, 204] },
    { id: 303, numero: 'PC-003', descripcion: 'Equipo en mantenimiento', idSalon: 102, activo: false, programas: [] },
    { id: 304, numero: 'PC-004', descripcion: 'Estación multimedia', idSalon: 104, activo: true, programas: [201, 202] },
    { id: 305, numero: 'LAP-001', descripcion: 'Equipo portátil de respaldo', idSalon: null, activo: true, programas: [205] },
  ];
  const defaultUsuarios = [
    { id: 401, nombre: 'Adriana', apellido: 'Méndez', correo: 'adriana.mendez@correo.test', rol: 'COORDINADOR', idPlantel: null, activo: true },
    { id: 402, nombre: 'Raúl', apellido: 'Castillo', correo: 'raul.castillo@correo.test', rol: 'ADMIN_PLANTEL', idPlantel: 1, activo: true },
    { id: 403, nombre: 'Laura', apellido: 'Pérez', correo: 'laura.perez@correo.test', rol: 'DOCENTE', idPlantel: 2, activo: true },
    { id: 404, nombre: 'Diego', apellido: 'Vargas', correo: 'diego.vargas@correo.test', rol: 'ALUMNO', idPlantel: 1, activo: false },
    { id: 405, nombre: 'Sofía', apellido: 'Torres', correo: 'sofia.torres@correo.test', rol: 'ADMIN_PLANTEL', idPlantel: 2, activo: true },
  ];

  const cloneDefaults = () => defaultPlanteles.map((item) => ({ ...item }));

  const readPlanteles = () => {
    try {
      const saved = window.localStorage.getItem(plantelesKey);
      if (!saved) return cloneDefaults();
      const parsed = JSON.parse(saved);
      return Array.isArray(parsed) ? parsed : cloneDefaults();
    } catch (error) {
      return cloneDefaults();
    }
  };

  const writePlanteles = (planteles) => {
    window.localStorage.setItem(plantelesKey, JSON.stringify(planteles));
  };

  const nextPlantelId = (planteles) => (
    planteles.reduce((highest, plantel) => Math.max(highest, Number(plantel.id) || 0), 0) + 1
  );

  const readSalones = () => {
    try {
      const saved = window.localStorage.getItem(salonesKey);
      if (!saved) return defaultSalones.map((item) => ({ ...item }));
      const parsed = JSON.parse(saved);
      return Array.isArray(parsed) ? parsed : defaultSalones.map((item) => ({ ...item }));
    } catch (error) {
      return defaultSalones.map((item) => ({ ...item }));
    }
  };

  const writeSalones = (salones) => {
    window.localStorage.setItem(salonesKey, JSON.stringify(salones));
  };

  const nextSalonId = (salones) => (
    salones.reduce((highest, salon) => Math.max(highest, Number(salon.id) || 0), 100) + 1
  );

  const readProgramas = () => {
    try {
      const saved = window.localStorage.getItem(programasKey);
      if (!saved) return defaultProgramas.map((item) => ({ ...item }));
      const parsed = JSON.parse(saved);
      return Array.isArray(parsed) ? parsed : defaultProgramas.map((item) => ({ ...item }));
    } catch (error) {
      return defaultProgramas.map((item) => ({ ...item }));
    }
  };

  const writeProgramas = (programas) => {
    window.localStorage.setItem(programasKey, JSON.stringify(programas));
  };

  const nextProgramaId = (programas) => (
    programas.reduce((highest, programa) => Math.max(highest, Number(programa.id) || 0), 200) + 1
  );

  const readEquipos = () => {
    try {
      const saved = window.localStorage.getItem(equiposKey);
      if (!saved) return defaultEquipos.map((item) => ({ ...item, programas: [...item.programas] }));
      const parsed = JSON.parse(saved);
      return Array.isArray(parsed) ? parsed : defaultEquipos.map((item) => ({ ...item, programas: [...item.programas] }));
    } catch (error) {
      return defaultEquipos.map((item) => ({ ...item, programas: [...item.programas] }));
    }
  };

  const writeEquipos = (equipos) => {
    window.localStorage.setItem(equiposKey, JSON.stringify(equipos));
  };

  const nextEquipoId = (equipos) => (
    equipos.reduce((highest, equipo) => Math.max(highest, Number(equipo.id) || 0), 300) + 1
  );

  const readUsuarios = () => {
    try {
      const saved = window.localStorage.getItem(usuariosKey);
      if (!saved) return defaultUsuarios.map((item) => ({ ...item }));
      const parsed = JSON.parse(saved);
      return Array.isArray(parsed) ? parsed : defaultUsuarios.map((item) => ({ ...item }));
    } catch (error) {
      return defaultUsuarios.map((item) => ({ ...item }));
    }
  };

  const writeUsuarios = (usuarios) => {
    window.localStorage.setItem(usuariosKey, JSON.stringify(usuarios));
  };

  const nextUsuarioId = (usuarios) => (
    usuarios.reduce((highest, usuario) => Math.max(highest, Number(usuario.id) || 0), 400) + 1
  );

  window.ScheduleMockData = {
    readPlanteles,
    writePlanteles,
    nextPlantelId,
    readSalones,
    writeSalones,
    nextSalonId,
    readProgramas,
    writeProgramas,
    nextProgramaId,
    readEquipos,
    writeEquipos,
    nextEquipoId,
    readUsuarios,
    writeUsuarios,
    nextUsuarioId,
  };
}());
