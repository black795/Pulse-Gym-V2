import { api, subirArchivo } from './http';
import type {
  Confirmacion, ConsentimientoEstado, DiaSemana, EjercicioFicha, EjercicioResumen, EstadoMaquina, Foto, GrupoMuscular, GymDetalle, GymMaquina, GymResumen,
  GymsRespuesta, Hoy, Lesion, LesionesRespuesta, MaquinaCatalogo, Medicion, Perfil, PerfilEnvio, PlanEstado, Reconocimiento,
  Sesion, TextoConsentimiento, Usuario, Zona,
} from './tipos';

export const authApi = {
  login: (email: string, password: string) => api<Sesion>('/auth/login', { method: 'POST', body: { email, password }, conToken: false }),
  registro: (d: { nombre: string; email: string; password: string }) => api<Sesion>('/auth/registro', { method: 'POST', body: d, conToken: false }),
  yo: () => api<Usuario>('/auth/me'),
  recuperar: (email: string) => api<{ mensaje: string }>('/auth/recuperar', { method: 'POST', body: { email }, conToken: false }),
  restablecer: (token: string, password: string) => api<{ mensaje: string }>('/auth/restablecer', { method: 'POST', body: { token, password }, conToken: false }),
};

export const perfilApi = {
  ver: () => api<Perfil>('/perfil'),
  guardar: (d: PerfilEnvio) => api<Perfil>('/perfil', { method: 'PUT', body: d }),
  mediciones: () => api<Medicion[]>('/mediciones'),
  textoConsentimiento: () => api<TextoConsentimiento>('/consentimiento/texto', { conToken: false }),
  fijarConsentimiento: (acepta: boolean) => api<ConsentimientoEstado>('/consentimiento', { method: 'PUT', body: { acepta } }),
  eliminarCuenta: () => api<null>('/cuenta', { method: 'DELETE' }),
};

export const lesionesApi = {
  zonas: () => api<Zona[]>('/zonas-lesion'),
  listar: () => api<LesionesRespuesta>('/lesiones'),
  crear: (d: { zona: string; tipo: 'aguda' | 'cronica'; duele_con_carga: boolean; descripcion?: string; estado?: 'activa' | 'reintroduccion' }) =>
    api<Lesion>('/lesiones', { method: 'POST', body: d }),
  cambiar: (id: number, d: Partial<{ estado: Lesion['estado']; descripcion: string; duele_con_carga: boolean }>) =>
    api<Lesion>(`/lesiones/${id}`, { method: 'PATCH', body: d }),
};

export const gymsApi = {
  listar: () => api<GymsRespuesta>('/gyms'),
  crear: (d: { nombre: string; ubicacion?: string }) => api<GymResumen>('/gyms', { method: 'POST', body: d }),
  ver: (id: number) => api<GymDetalle>(`/gyms/${id}`),
  cambiar: (id: number, d: { nombre?: string; ubicacion?: string | null }) => api<GymResumen>(`/gyms/${id}`, { method: 'PATCH', body: d }),
  eliminar: (id: number) => api<null>(`/gyms/${id}`, { method: 'DELETE' }),
  usar: (id: number) => api<GymResumen>(`/gyms/${id}/usar`, { method: 'POST' }),
  implementos: (id: number, d: { implementos: string[]; mancuernas_max_kg?: number | null }) =>
    api<GymDetalle>(`/gyms/${id}/implementos`, { method: 'PUT', body: d }),
  estadoMaquina: (id: number, gmId: number, estado: EstadoMaquina) =>
    api<GymMaquina>(`/gyms/${id}/maquinas/${gmId}`, { method: 'PATCH', body: { estado } }),
  agregarMaquina: (id: number, codigo: string) =>
    api<GymMaquina>(`/gyms/${id}/maquinas`, { method: 'POST', body: { codigo } }),
  quitarMaquina: (id: number, gmId: number) => api<null>(`/gyms/${id}/maquinas/${gmId}`, { method: 'DELETE' }),
  subirFoto: (id: number, foto: Blob, alProgreso: (pct: number) => void) =>
    subirArchivo<Foto>(`/gyms/${id}/fotos`, 'archivo', foto, foto.type === 'image/jpeg' ? 'maquina.jpg' : 'maquina', alProgreso),
};

export const fotosApi = {
  // PG-08: si la IA tarda más de 15 s el backend responde con error; el límite de 20 s cubre también la red.
  reconocer: (id: number) => api<Reconocimiento>(`/fotos/${id}/reconocer`, { method: 'POST', limiteMs: 20_000 }),
  confirmar: (id: number, d: { codigo: string; origen: 'sugerencia' | 'manual'; reemplazar_foto?: boolean }) =>
    api<Confirmacion>(`/fotos/${id}/confirmar`, { method: 'POST', body: d }),
  ninguna: (id: number) => api<Foto>(`/fotos/${id}/ninguna`, { method: 'POST' }),
  descartar: (id: number) => api<null>(`/fotos/${id}`, { method: 'DELETE' }),
};

export const catalogoApi = {
  maquinas: (f: { q?: string; grupo?: string } = {}) => {
    const p = new URLSearchParams();
    if (f.q) p.set('q', f.q);
    if (f.grupo) p.set('grupo', f.grupo);
    return api<MaquinaCatalogo[]>(`/catalogo/maquinas${p.size ? `?${p}` : ''}`);
  },
  grupos: () => api<GrupoMuscular[]>('/catalogo/grupos-musculares'),
  ejercicios: (f: { grupo?: string; categoria?: string; maquina?: string } = {}) => {
    const p = new URLSearchParams();
    if (f.grupo) p.set('grupo', f.grupo);
    if (f.categoria) p.set('categoria', f.categoria);
    if (f.maquina) p.set('maquina', f.maquina);
    return api<EjercicioResumen[]>(`/catalogo/ejercicios${p.size ? `?${p}` : ''}`);
  },
  ficha: (id: number) => api<EjercicioFicha>(`/catalogo/ejercicios/${id}`),
};

/** La fecha local del celular (AAAA-MM-DD): el "hoy" del usuario, no el del servidor. */
export const fechaLocal = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

export const planApi = {
  // PG-23: el plan se arma en menos de 20 s (si se regenera por una lesión nueva, también al pedirlo).
  ver: () => api<PlanEstado>('/plan', { limiteMs: 30_000 }),
  generar: (dias?: DiaSemana[]) => api<PlanEstado>('/plan', { method: 'POST', body: dias ? { dias } : {}, limiteMs: 30_000 }),
  // PG-28: la adaptación tarda menos de 10 s.
  hoy: (f: { gym_id?: number; dia?: DiaSemana } = {}) => {
    const p = new URLSearchParams({ fecha: fechaLocal() });
    if (f.gym_id != null) p.set('gym_id', String(f.gym_id));
    if (f.dia) p.set('dia', f.dia);
    return api<Hoy>(`/hoy?${p}`, { limiteMs: 30_000 });
  },
};
