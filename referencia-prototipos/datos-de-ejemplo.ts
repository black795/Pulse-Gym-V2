export const staff = [
  { id: 1, name: 'Carlos Mendoza', role: 'Dueño', initial: 'C', color: '#16A34A' },
  { id: 2, name: 'Pati Ríos', role: 'Recepcionista', initial: 'P', color: '#0891b2' },
  { id: 3, name: 'Javier Torres', role: 'Entrenador', initial: 'J', color: '#7c3aed' },
  { id: 4, name: 'Rosa Lima', role: 'Entrenadora', initial: 'R', color: '#db2777' },
  { id: 5, name: 'Iván Castillo', role: 'Entrenador', initial: 'I', color: '#d97706' },
];

export const clients = [
  {
    id: 1,
    name: 'Daniela Vargas',
    phone: '+591 70012345',
    plan: 'Trimestral',
    lastVisit: '17 sep 2026',
    status: 'active',
    photo: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&h=200&fit=crop&auto=format',
    weight: 58,
    height: 165,
    age: 27,
    goal: 'Fuerza',
    injury: { zone: 'Rodilla derecha', severity: 'Moderada', date: '02 sep 2026', trainer: 'Rosa Lima' },
    measurements: [
      { date: '17 sep 2026', weight: 58, bmi: 21.3, arms: 30, waist: 68, hips: 92 },
      { date: '01 sep 2026', weight: 59, bmi: 21.7, arms: 29.5, waist: 69, hips: 93 },
      { date: '15 ago 2026', weight: 60, bmi: 22.0, arms: 29, waist: 70, hips: 94 },
    ],
    routine: {
      assignedBy: 'Rosa Lima',
      days: ['Lunes', 'Miércoles', 'Viernes'],
      schedule: {
        Lunes: [
          { id: 1, name: 'Sentadilla con barra', sets: 4, reps: '10', weight: '60 kg', prev: '55 kg', available: true, progress: '+5 kg en 3 semanas' },
          { id: 2, name: 'Prensa de piernas', sets: 3, reps: '12', weight: '80 kg', prev: '72 kg', available: true, progress: '+8 kg en 4 semanas' },
          { id: 3, name: 'Extensión de cuádriceps', sets: 3, reps: '15', weight: '35 kg', prev: '30 kg', available: false, planB: true },
          { id: 4, name: 'Curl femoral', sets: 3, reps: '12', weight: '25 kg', prev: '22 kg', available: true },
        ],
        Miércoles: [
          { id: 5, name: 'Press de banca', sets: 4, reps: '8', weight: '45 kg', prev: '42 kg', available: true },
          { id: 6, name: 'Remo en polea baja', sets: 3, reps: '12', weight: '50 kg', prev: '45 kg', available: false, planB: true },
          { id: 7, name: 'Jalón al pecho', sets: 3, reps: '10', weight: '40 kg', prev: '37 kg', available: true },
        ],
        Viernes: [
          { id: 8, name: 'Plancha abdominal', sets: 3, reps: '45s', weight: '--', prev: '--', available: true },
          { id: 9, name: 'Peso muerto rumano', sets: 4, reps: '10', weight: '55 kg', prev: '50 kg', available: true },
          { id: 10, name: 'Hip thrust', sets: 3, reps: '12', weight: '60 kg', prev: '55 kg', available: true },
        ],
      },
    },
  },
  {
    id: 2,
    name: 'Emerson Choque',
    phone: '+591 71123456',
    plan: 'Mensual',
    lastVisit: '16 sep 2026',
    status: 'active',
    photo: null,
    weight: 75,
    height: 178,
    age: 31,
    goal: 'Masa muscular',
    injury: null,
    measurements: [{ date: '10 sep 2026', weight: 75, bmi: 23.7, arms: 36, waist: 82, hips: 96 }],
  },
  {
    id: 3,
    name: 'Valeria Prado',
    phone: '+591 72234567',
    plan: 'Semestral',
    lastVisit: '15 sep 2026',
    status: 'active',
    photo: null,
    weight: 54,
    height: 160,
    age: 24,
    goal: 'Pérdida de grasa',
    injury: null,
    measurements: [{ date: '08 sep 2026', weight: 54, bmi: 21.1, arms: 27, waist: 65, hips: 88 }],
  },
  {
    id: 4,
    name: 'Ronald Quispe',
    phone: '+591 73345678',
    plan: 'Mensual',
    lastVisit: '29 ago 2026',
    status: 'overdue',
    photo: null,
    weight: 82,
    height: 175,
    age: 35,
    goal: 'Salud general',
    injury: null,
    measurements: [{ date: '25 ago 2026', weight: 82, bmi: 26.8, arms: 38, waist: 90, hips: 102 }],
  },
  {
    id: 5,
    name: 'Fátima Delgado',
    phone: '+591 74456789',
    plan: 'Trimestral',
    lastVisit: '17 sep 2026',
    status: 'active',
    photo: null,
    weight: 61,
    height: 163,
    age: 29,
    goal: 'Acondicionamiento',
    injury: null,
    measurements: [{ date: '12 sep 2026', weight: 61, bmi: 22.9, arms: 29, waist: 72, hips: 90 }],
  },
  {
    id: 6,
    name: 'Bruno Salazar',
    phone: '+591 75567890',
    plan: 'Mensual',
    lastVisit: '10 sep 2026',
    status: 'warning',
    photo: null,
    weight: 79,
    height: 180,
    age: 33,
    goal: 'Fuerza',
    injury: { zone: 'Zona lumbar', severity: 'Leve', date: '05 sep 2026', trainer: 'Javier Torres' },
    measurements: [{ date: '10 sep 2026', weight: 79, bmi: 24.4, arms: 37, waist: 86, hips: 99 }],
  },
];

export const machines = [
  { id: 1, name: 'Prensa de piernas', group: 'Piernas', status: 'available', image: 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400&h=300&fit=crop&auto=format' },
  { id: 2, name: 'Banco de press', group: 'Pecho', status: 'occupied', image: null },
  { id: 3, name: 'Polea alta', group: 'Espalda', status: 'available', image: 'https://images.unsplash.com/photo-1571902943202-507ec2618e8f?w=400&h=300&fit=crop&auto=format' },
  { id: 4, name: 'Extensión de cuádriceps', group: 'Piernas', status: 'maintenance', image: null },
  { id: 5, name: 'Caminadora', group: 'Cardio', status: 'available', image: 'https://images.unsplash.com/photo-1538805060514-97d9cc17730c?w=400&h=300&fit=crop&auto=format' },
  { id: 6, name: 'Elíptica', group: 'Cardio', status: 'available', image: null },
];

export const payments = [
  { id: 1, date: '17 sep 2026', client: 'Daniela Vargas', plan: 'Trimestral', amount: 400, method: 'QR', status: 'paid' },
  { id: 2, date: '16 sep 2026', client: 'Emerson Choque', plan: 'Mensual', amount: 150, method: 'Efectivo', status: 'paid' },
  { id: 3, date: '15 sep 2026', client: 'Valeria Prado', plan: 'Semestral', amount: 700, method: 'Tarjeta', status: 'paid' },
  { id: 4, date: '14 sep 2026', client: 'Ronald Quispe', plan: 'Mensual', amount: 150, method: 'Efectivo', status: 'pending' },
  { id: 5, date: '12 sep 2026', client: 'Fátima Delgado', plan: 'Trimestral', amount: 400, method: 'QR', status: 'paid' },
  { id: 6, date: '10 sep 2026', client: 'Bruno Salazar', plan: 'Mensual', amount: 150, method: 'Tarjeta', status: 'paid' },
];

export const attendance = [
  { id: 1, client: 'Daniela Vargas', time: '07:02', method: 'QR', date: '17 sep 2026' },
  { id: 2, client: 'Fátima Delgado', time: '07:45', method: 'QR', date: '17 sep 2026' },
  { id: 3, client: 'Emerson Choque', time: '08:10', method: 'Manual', date: '17 sep 2026' },
  { id: 4, client: 'Valeria Prado', time: '09:30', method: 'QR', date: '17 sep 2026' },
  { id: 5, client: 'Bruno Salazar', time: '18:00', method: 'Manual', date: '17 sep 2026' },
];

export const injuries = [
  { id: 1, client: 'Daniela Vargas', injury: 'Lesión rodilla derecha', date: '02 sep 2026', routineAdjusted: true, trainer: 'Rosa Lima' },
  { id: 2, client: 'Bruno Salazar', injury: 'Dolor zona lumbar', date: '05 sep 2026', routineAdjusted: false, trainer: 'Javier Torres' },
];

export const revenueData = [
  { month: 'Abr', amount: 4800 },
  { month: 'May', amount: 5200 },
  { month: 'Jun', amount: 4600 },
  { month: 'Jul', amount: 5900 },
  { month: 'Ago', amount: 6200 },
  { month: 'Sep', amount: 5800 },
];

export const kpis = {
  activeClients: 5,
  activeMembers: 4,
  todayAttendance: 5,
  activeTrainers: 3,
};

export const recentActivity = [
  { id: 1, text: 'Daniela Vargas registró ingreso', time: 'hace 2h', type: 'attendance' },
  { id: 2, text: 'Nuevo pago: Fátima Delgado — Bs 400', time: 'hace 3h', type: 'payment' },
  { id: 3, text: 'Rutina actualizada para Daniela Vargas', time: 'hace 5h', type: 'routine' },
  { id: 4, text: 'Emerson Choque registró ingreso', time: 'hace 6h', type: 'attendance' },
  { id: 5, text: 'Bruno Salazar — lesión lumbar registrada', time: 'hace 1d', type: 'injury' },
];

export const alerts = [
  { id: 1, text: 'Bruno Salazar tiene lesión lumbar sin rutina ajustada', type: 'danger' },
  { id: 2, text: 'Ronald Quispe — membresía vencida hace 18 días', type: 'danger' },
  { id: 3, text: '2 membresías vencen en los próximos 7 días', type: 'warning' },
  { id: 4, text: 'Extensión de cuádriceps en mantenimiento', type: 'warning' },
];

export const planBOptions = [
  { id: 1, label: 'Polea baja alternativa', description: 'Máquina similar disponible — Polea alta en agarre neutro', available: true, selected: true },
  { id: 2, label: 'Alternativa en calistenia', description: 'Remo invertido con barra — Sin equipamiento necesario', available: true, selected: false },
  { id: 3, label: 'Saltar al siguiente', description: 'Continuar con el ejercicio siguiente de la rutina', available: true, selected: false },
];

export const aiMessages = [
  { id: 1, role: 'ai', text: 'Hola Daniela 👋 Revisé tu perfil y tengo una actualización importante para tu rutina de hoy.' },
  { id: 2, role: 'ai', text: 'Detecté que tienes una lesión activa en la rodilla derecha registrada el 2 de septiembre. He ajustado automáticamente tu rutina para proteger esa zona.' },
  { id: 3, role: 'user', text: '¿Qué cambios hiciste?' },
  { id: 4, role: 'ai', text: 'Reemplacé la extensión de cuádriceps por ejercicios de bajo impacto: elevaciones de talón y trabajo de isquiotibiales con resistencia leve. También reduje la carga en sentadillas en un 15%.' },
  { id: 5, role: 'ai', text: 'Además, la polea baja está ocupada ahora mismo. Te propongo 3 alternativas para ese ejercicio. ¿Cuál prefieres?' },
];
