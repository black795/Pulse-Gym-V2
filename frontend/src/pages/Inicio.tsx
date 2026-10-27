/**
 * Inicio = "Hoy" (PG-28). Si tienes más de un gym, lo primero es elegir dónde estás (el último usado va primero y
 * preseleccionado); con uno solo se salta. Luego se ve el día que toca del plan adaptado a las máquinas de ese gym,
 * con qué ejercicios cambiaron y por qué. Si hoy no toca, se ofrece adelantar el siguiente día.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router';
import { Aviso, Insignia } from '../components/UI';
import { IconCamera, IconDumbbell, IconLock, IconMapPin, IconZap } from '../components/Icons';
import { useAuth } from '../features/auth/AuthContext';
import { fechaLocal, gymsApi, planApi } from '../lib/endpoints';
import { ApiError } from '../lib/http';
import type { DiaSemana, Hoy } from '../lib/tipos';
import { usePerfil } from '../lib/usePerfil';
import { EQUIPO, descanso, repeticiones } from './Plan';

const ETIQUETAS: Record<string, string> = {
  edad: 'edad', sexo: 'sexo', altura_cm: 'altura', peso_kg: 'peso', objetivo: 'objetivo', nivel: 'nivel',
  dias_por_semana: 'días por semana', minutos_por_sesion: 'minutos por sesión',
};

// El gym elegido se recuerda solo por hoy: mañana se vuelve a preguntar.
const CLAVE_GYM = 'pulse.gymDeHoy';
function gymGuardado(): number | null {
  try {
    const g = JSON.parse(localStorage.getItem(CLAVE_GYM) ?? 'null') as { fecha: string; gymId: number } | null;
    return g && g.fecha === fechaLocal() ? g.gymId : null;
  } catch { return null; }
}
function guardarGym(gymId: number | null) {
  try {
    if (gymId == null) localStorage.removeItem(CLAVE_GYM);
    else localStorage.setItem(CLAVE_GYM, JSON.stringify({ fecha: fechaLocal(), gymId }));
  } catch { /* sin almacenamiento: se vuelve a preguntar */ }
}

export default function Inicio() {
  const { usuario } = useAuth();
  const { perfil, error: errorPerfil } = usePerfil();
  const [hoy, setHoy] = useState<Hoy | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eligiendo, setEligiendo] = useState(false);
  const [seleccion, setSeleccion] = useState<number | null>(null);
  const [adelantado, setAdelantado] = useState<DiaSemana | null>(null);
  const primerNombre = usuario?.nombre.split(' ')[0] ?? '';

  const cargar = useCallback(async (gymId: number | null, dia: DiaSemana | null) => {
    setCargando(true); setError(null);
    try {
      const h = await planApi.hoy({ gym_id: gymId ?? undefined, dia: dia ?? undefined });
      setHoy(h);
      setEligiendo(h.requiere_elegir_gym);
      setSeleccion(s => s ?? h.gyms[0]?.id ?? null); // el último usado, preseleccionado
    } catch (e) {
      if (e instanceof ApiError && e.status === 404 && gymId != null) { guardarGym(null); return cargar(null, dia); } // ese gym ya no existe
      setError(e instanceof Error ? e.message : 'No se pudo cargar tu sesión de hoy.');
    } finally { setCargando(false); }
  }, []);

  useEffect(() => { void cargar(gymGuardado(), null); }, [cargar]);

  async function elegirGym() {
    if (seleccion == null) return;
    guardarGym(seleccion);
    void gymsApi.usar(seleccion).catch(() => {}); // PG-06: se recuerda el último gym usado
    await cargar(seleccion, adelantado);
  }

  function adelantar(dia: DiaSemana) {
    setAdelantado(dia);
    void cargar(gymGuardado(), dia);
  }

  const sesion = hoy?.sesion;
  const variosGyms = (hoy?.gyms.length ?? 0) > 1;

  return (
    <div className="pantalla stack" style={{ gap: 16 }}>
      <header style={{ padding: '8px 0 4px' }}>
        <p className="muted" style={{ fontSize: 14 }}>Hola,</p>
        <h1 style={{ fontSize: 26 }}>{primerNombre} 👋</h1>
      </header>

      {(errorPerfil || error) && <Aviso>{errorPerfil ?? error}</Aviso>}

      {perfil && !perfil.puede_generar_plan && (
        <div className="card stack" style={{ gap: 10, borderColor: 'var(--primary)' }}>
          <h2 style={{ fontSize: 17 }}>Completa tu perfil</h2>
          <p className="muted" style={{ fontSize: 14 }}>
            Para armar tu plan nos falta: {perfil.faltan.map(c => ETIQUETAS[c] ?? c).join(', ')}.
          </p>
          <Link to="/onboarding" className="btn">Completar en 3 pasos</Link>
        </div>
      )}

      {perfil && perfil.consentimiento.estado === 'pendiente' && (
        <Link to="/consentimiento" className="card fila" style={{ textDecoration: 'none', color: 'inherit' }}>
          <IconLock width={22} height={22} style={{ color: 'var(--primary-dark)', flexShrink: 0 }} />
          <span style={{ fontSize: 14 }}><b>Decide sobre tus datos de salud.</b> Necesitamos tu permiso para guardar peso, medidas y lesiones.</span>
        </Link>
      )}

      {cargando && !hoy && <p className="muted pulse-latido" style={{ textAlign: 'center', padding: 20 }}>Preparando tu sesión de hoy…</p>}

      {hoy && !hoy.plan_existe && perfil?.puede_generar_plan && (
        <Link to="/plan" className="card stack" style={{ gap: 8, textDecoration: 'none', color: 'inherit', borderColor: 'var(--primary)' }}>
          <div className="fila"><IconZap style={{ color: 'var(--primary-dark)' }} /><h2 style={{ fontSize: 17 }}>Arma tu plan semanal</h2></div>
          <p className="muted" style={{ fontSize: 14 }}>Elige qué días entrenas y la IA arma tu semana según tu objetivo y tus lesiones.</p>
        </Link>
      )}

      {hoy && hoy.gyms.length === 0 && (
        <Link to="/gyms" className="card stack" style={{ gap: 8, textDecoration: 'none', color: 'inherit' }}>
          <div className="fila"><IconCamera style={{ color: 'var(--primary-dark)' }} /><h2 style={{ fontSize: 17 }}>Registra tu gym</h2></div>
          <p className="muted" style={{ fontSize: 14 }}>Toma fotos de las máquinas y adaptamos cada sesión a lo que realmente tienes.</p>
        </Link>
      )}

      {/* PG-28: elegir el gym (el último usado, primero y preseleccionado) */}
      {hoy && eligiendo && (
        <section className="card stack" aria-labelledby="donde">
          <h2 id="donde" style={{ fontSize: 17 }}>¿En qué gym estás hoy?</h2>
          <div className="opciones">
            {hoy.gyms.map(g => (
              <button key={g.id} type="button" className="opcion fila" style={{ justifyContent: 'space-between' }}
                aria-pressed={seleccion === g.id} onClick={() => setSeleccion(g.id)}>
                <span>{g.nombre}<br /><span className="muted" style={{ fontSize: 12.5, fontWeight: 500 }}>{g.maquinas} máquinas</span></span>
                {g.es_ultimo_usado && <Insignia tono="ok">Último usado</Insignia>}
              </button>
            ))}
          </div>
          <button className="btn" disabled={seleccion == null || cargando} onClick={elegirGym}>{cargando ? 'Adaptando tu sesión…' : 'Continuar'}</button>
        </section>
      )}

      {/* Hoy no toca: ofrecer adelantar */}
      {hoy && hoy.plan_existe && !sesion && !eligiendo && hoy.siguiente_dia && (
        <section className="card stack" style={{ gap: 10 }}>
          <h2 style={{ fontSize: 17 }}>Hoy, {hoy.dia_nombre.toLowerCase()}, descansas 😌</h2>
          <p className="muted" style={{ fontSize: 14 }}>
            Descansar también es parte del plan. Tu próximo día es el {hoy.siguiente_dia.dia_nombre.toLowerCase()}: {hoy.siguiente_dia.enfoque.toLowerCase()}.
          </p>
          <button className="btn btn-claro" disabled={cargando} onClick={() => adelantar(hoy.siguiente_dia!.dia)}>
            Adelantar el {hoy.siguiente_dia.dia_nombre.toLowerCase()}
          </button>
        </section>
      )}

      {sesion && !eligiendo && (
        <section className="hero-hoy stack" aria-labelledby="sesion-hoy">
          <div className="fila" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <span className="etiqueta-neon">{sesion.dia === hoy!.dia ? 'HOY' : 'ADELANTADO'} · {sesion.dia_nombre.toUpperCase()}</span>
            {sesion.gym_nombre && (
              <button className="pill-gym" disabled={!variosGyms || cargando} onClick={() => setEligiendo(true)}>
                <IconMapPin width={15} height={15} /> {sesion.gym_nombre}{variosGyms ? ' · Cambiar' : ''}
              </button>
            )}
          </div>
          <h2 id="sesion-hoy" style={{ fontSize: 22, color: '#fff' }}>{sesion.enfoque}</h2>
          <p style={{ fontSize: 13.5, color: '#b9cbbf' }}>
            {sesion.ejercicios.length} ejercicios · ~{sesion.minutos_estimados} min
            {sesion.cambios > 0
              ? ` · ${sesion.origen === 'ia' ? 'La IA adaptó' : 'Adaptamos'} ${sesion.cambios} ${sesion.cambios === 1 ? 'ejercicio' : 'ejercicios'} a este gym`
              : ' · Todo disponible en este gym'}
          </p>
          {cargando && <p className="pulse-latido" style={{ fontSize: 13, color: 'var(--neon)' }}>Adaptando…</p>}
        </section>
      )}

      {sesion && !eligiendo && (
        <>
          {sesion.avisos.map(a => <Aviso key={a} tipo="info">{a}</Aviso>)}
          {sesion.sugerir_fotos && sesion.gym_id && (
            <Link to={`/gyms/${sesion.gym_id}/agregar`} className="btn btn-claro"><IconCamera width={18} height={18} /> Tomar fotos de las máquinas</Link>
          )}
          <div className="stack" style={{ gap: 10 }}>
            {sesion.ejercicios.map(e => (
              <article key={e.orden} className="card ejercicio" style={e.cambio ? { borderColor: 'var(--warning-tint)' } : undefined}>
                <span className="ejercicio-orden">{e.orden}</span>
                <div className="stack" style={{ gap: 4, minWidth: 0 }}>
                  <div className="fila" style={{ gap: 8, flexWrap: 'wrap' }}>
                    <b style={{ fontSize: 15 }}>{e.ejercicio.nombre}</b>
                    {e.cambio && <Insignia tono="aviso">Cambiado</Insignia>}
                    {e.precaucion && <Insignia tono="peligro">Con precaución</Insignia>}
                  </div>
                  <span className="muted" style={{ fontSize: 12.5 }}>
                    {e.ejercicio.musculo_principal} · {e.ejercicio.maquinas.length ? e.ejercicio.maquinas.join(' o ') : EQUIPO[e.ejercicio.categoria_equipo]}
                  </span>
                  <span style={{ fontSize: 14, fontWeight: 700 }}>{e.series} × {repeticiones(e.reps_min, e.reps_max)} reps · descanso {descanso(e.descanso_seg)}</span>
                  {e.cambio && e.original && (
                    <p className="cambio-nota">
                      En tu plan: <b>{e.original.nombre}</b>. {e.motivo_cambio} {e.por_que_reemplazo}
                    </p>
                  )}
                </div>
              </article>
            ))}
            {sesion.omitidos.map(o => <Aviso key={o.nombre} tipo="info"><b>{o.nombre}:</b> {o.motivo}</Aviso>)}
          </div>
          <p className="muted" style={{ fontSize: 12.5, textAlign: 'center' }}>
            Iniciar la rutina con cronómetro y registro de series llega con la sesión en vivo (Sprint 4).
          </p>
        </>
      )}

      {hoy?.plan_existe && (
        <Link to="/plan" className="card fila" style={{ textDecoration: 'none', color: 'inherit', gap: 12 }}>
          <IconDumbbell style={{ color: 'var(--primary-dark)', flexShrink: 0 }} />
          <span className="stack" style={{ gap: 2 }}>
            <b style={{ fontSize: 15 }}>Ver mi plan semanal</b>
            <span className="muted" style={{ fontSize: 13 }}>La semana completa y por qué te tocó cada ejercicio.</span>
          </span>
        </Link>
      )}
    </div>
  );
}
