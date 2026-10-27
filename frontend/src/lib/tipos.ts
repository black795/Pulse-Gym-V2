export type EstadoConsentimiento = 'pendiente' | 'aceptado' | 'rechazado';

export interface Usuario {
  id: number; nombre: string; email: string;
  consentimiento_estado: EstadoConsentimiento; perfil_completo: boolean; created_at: string;
}
export interface Sesion { access_token: string; token_type: string; expira_en_dias: number; usuario: Usuario }

export interface Medicion { fecha: string; peso_kg: number | null; grasa_pct: number | null; masa_muscular_kg: number | null }
export interface ConsentimientoEstado {
  estado: EstadoConsentimiento; version_aceptada: string | null; aceptado_at: string | null; version_vigente: string;
}
export interface Perfil {
  nombre: string; email: string; edad: number | null; sexo: string | null; altura_cm: number | null;
  descanso_default_seg: number; objetivo: string | null; nivel: string | null;
  dias_por_semana: number | null; minutos_por_sesion: number | null;
  ultima_medicion: Medicion | null; imc: number | null; imc_categoria: string | null;
  faltan: string[]; puede_generar_plan: boolean; plan_requiere_regenerar: boolean; consentimiento: ConsentimientoEstado;
}
export interface PerfilEnvio {
  edad?: number; sexo?: string; peso_kg?: number; altura_cm?: number; grasa_pct?: number; masa_muscular_kg?: number;
  objetivo?: string; nivel?: string; dias_por_semana?: number; minutos_por_sesion?: number; descanso_default_seg?: number;
}
export interface TextoConsentimiento { version: string; titulo: string; secciones: { titulo: string; texto: string }[] }

export interface Zona { codigo: string; nombre: string }
export interface Lesion {
  id: number; zona: Zona; tipo: 'aguda' | 'cronica'; duele_con_carga: boolean; descripcion: string | null;
  estado: 'activa' | 'reintroduccion' | 'recuperada'; created_at: string; recuperada_at: string | null;
}
export interface LesionesRespuesta { aviso: string; lesiones: Lesion[] }

// ---------------- Sprint 2: mis gyms y fotos ----------------
export type EstadoMaquina = 'disponible' | 'malograda' | 'retirada';

export interface MaquinaOpcion { codigo: string; nombre: string; tipo: string; foto_ref: string | null; musculo_principal: string | null }
export interface MaquinaCatalogo {
  id: number; codigo: string; nombre: string; otros_nombres: string[]; tipo: string; fotos: string[]; ejercicios: number;
  musculo_principal: string | null;
}
export interface GrupoMuscular { codigo: string; nombre: string }

export interface MaquinaResumen { codigo: string; nombre: string }
export interface Contraindicacion { zona: string; zona_nombre: string; nivel: 'evitar' | 'precaucion' }
export interface EjercicioResumen {
  id: number; codigo: string; nombre: string; musculo_principal: string | null;
  dificultad: string; categoria_equipo: string; maquinas: MaquinaResumen[];
}
export interface EjercicioFicha extends EjercicioResumen {
  musculos_secundarios: string[]; multiarticular: boolean; instrucciones: string;
  contraindicaciones: Contraindicacion[]; contraindicaciones_revisadas: boolean;
}

export interface GymMaquina {
  id: number; maquina: MaquinaOpcion; estado: EstadoMaquina; estado_at: string; foto_url: string | null; agregada_at: string;
  historial_estados: { estado: EstadoMaquina; fecha: string }[];
}
export interface Implemento { codigo: string; nombre: string; marcado: boolean }
export interface GymResumen {
  id: number; nombre: string; ubicacion: string | null; maquinas: number; implementos: number;
  ultimo_uso_at: string | null; es_ultimo_usado: boolean; created_at: string;
}
export interface GymDetalle extends GymResumen { inventario: GymMaquina[]; lista_implementos: Implemento[]; mancuernas_max_kg: number | null }
export interface GymsRespuesta { gyms: GymResumen[]; maximo: number }

export interface Foto { id: number; gym_id: number; estado: string; url: string; tomada_at: string }
export interface Sugerencia { puesto: number; confianza: number; maquina: MaquinaOpcion; ya_en_inventario: boolean }
export interface Reconocimiento {
  foto: Foto; es_maquina_de_gym: boolean; confianza_alta: boolean; umbral_alta: number;
  sugerencias: Sugerencia[]; modelo: string; duracion_ms: number;
}
export interface Confirmacion { accion: 'agregada' | 'foto_actualizada'; gym_maquina: GymMaquina }

// ---------------- Sprint 3: plan semanal y sesión de hoy ----------------
export type DiaSemana = 'lunes' | 'martes' | 'miercoles' | 'jueves' | 'viernes' | 'sabado' | 'domingo';

export interface EjercicioBreve {
  id: number; codigo: string; nombre: string; musculo_principal: string | null; categoria_equipo: string; maquinas: string[];
}
export interface RutinaEjercicio {
  id: number; orden: number; ejercicio: EjercicioBreve; series: number; reps_min: number; reps_max: number;
  descanso_seg: number; motivo: string; precaucion: boolean;
}
export interface RutinaDia {
  id: number; dia: DiaSemana; dia_nombre: string; enfoque: string; grupos: string[]; explicacion: string;
  minutos_estimados: number; ejercicios: RutinaEjercicio[];
}
export interface Plan {
  id: number; version: number; origen: 'ia' | 'mixto' | 'reglas'; modelo: string | null; motivo: string; esquema: string;
  esquema_texto: string; objetivo_tipo: string; explicacion: string; avisos: string[];
  lesiones: { zona: string; nombre: string; estado: 'activa' | 'reintroduccion' }[]; ejercicios_excluidos: number;
  creada_at: string; duracion_ms: number; dias: RutinaDia[];
}
export interface PlanEstado {
  plan: Plan | null; puede_generar: boolean; faltan: string[]; dias_sugeridos: DiaSemana[];
  regeneraciones_restantes: number; regeneraciones_max: number; perfil_cambio: boolean;
}

export interface EjercicioHoy {
  orden: number; ejercicio: EjercicioBreve; original: EjercicioBreve | null; cambio: boolean;
  motivo_cambio: string | null; por_que_reemplazo: string | null; precaucion: boolean;
  series: number; reps_min: number; reps_max: number; descanso_seg: number;
}
export interface SesionHoy {
  dia: DiaSemana; dia_nombre: string; enfoque: string; gym_id: number | null; gym_nombre: string | null;
  origen: 'ia' | 'reglas'; modelo: string | null; ejercicios: EjercicioHoy[]; cambios: number;
  omitidos: { nombre: string; motivo: string }[]; avisos: string[]; sugerir_fotos: boolean; minutos_estimados: number;
  duracion_ms: number;
}
export interface Hoy {
  fecha: string; dia: DiaSemana; dia_nombre: string; plan_existe: boolean; es_dia_de_entreno: boolean;
  siguiente_dia: { dia: DiaSemana; dia_nombre: string; enfoque: string } | null;
  gyms: { id: number; nombre: string; es_ultimo_usado: boolean; maquinas: number }[];
  requiere_elegir_gym: boolean; sesion: SesionHoy | null;
}
