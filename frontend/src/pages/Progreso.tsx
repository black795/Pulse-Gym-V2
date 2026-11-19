/**
 * Mi progreso (Sprint 5): constancia y racha (PG-38), alertas de retorno y estancamiento (PG-42, PG-43), historial
 * de máquinas y pesos con récords (PG-40, solo lo que ya hiciste), historial de sesiones (PG-46) y el acceso a
 * registrar un entrenamiento pasado (PG-39).
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { IconChevronRight, IconFlame, IconMapPin, IconPause, IconPlus, IconRefresh, IconTrophy } from '../components/Icons';
import { kg, LineaPeso } from '../components/PesoSugerido';
import { Aviso, Insignia } from '../components/UI';
import { progresoApi } from '../lib/endpoints';
import type { Alerta, Constancia, EjercicioUsado, EstadoTerminada, HistorialSesiones } from '../lib/tipos';
import { usePerfil } from '../lib/usePerfil';
import { EQUIPO } from './Plan';

type Filtro = 'maquina' | 'peso_libre' | 'sin_equipo' | 'todos';
const FILTROS: { valor: Filtro; texto: string }[] = [
  { valor: 'maquina', texto: 'Máquinas' }, { valor: 'peso_libre', texto: 'Peso libre' },
  { valor: 'sin_equipo', texto: 'Sin equipo' }, { valor: 'todos', texto: 'Todos' },
];
export const ESTADO: Record<EstadoTerminada, { texto: string; tono: 'ok' | 'aviso' | 'neutro' }> = {
  completa: { texto: 'Completa', tono: 'ok' }, parcial: { texto: 'Parcial', tono: 'aviso' }, manual: { texto: 'Manual', tono: 'neutro' },
};

/** "2026-11-10" → "10 nov" (sin pasar por UTC, para que no cambie de día). */
export function fechaCorta(iso: string, conAnio = false) {
  const [a, m, d] = iso.split('-').map(Number);
  return new Date(a, m - 1, d).toLocaleDateString('es', { day: 'numeric', month: 'short', ...(conAnio ? { year: 'numeric' } : {}) });
}
export const marca = (peso: number, reps: number) => (peso > 0 ? `${kg(peso)} × ${reps}` : `${reps} reps`);

export default function Progreso() {
  const { perfil } = usePerfil();
  const [constancia, setConstancia] = useState<Constancia | null>(null);
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [ejercicios, setEjercicios] = useState<EjercicioUsado[] | null>(null);
  const [historial, setHistorial] = useState<HistorialSesiones | null>(null);
  const [filtro, setFiltro] = useState<Filtro | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargandoMas, setCargandoMas] = useState(false);

  useEffect(() => {
    Promise.all([progresoApi.constancia(), progresoApi.alertas(), progresoApi.ejercicios(), progresoApi.historial()])
      .then(([c, a, e, h]) => { setConstancia(c); setAlertas(a.alertas); setEjercicios(e.ejercicios); setHistorial(h); })
      .catch(e => setError(e instanceof Error ? e.message : 'No se pudo cargar tu progreso.'));
  }, []);

  async function verMas() {
    if (!historial) return;
    setCargandoMas(true);
    try {
      const h = await progresoApi.historial(historial.pagina + 1);
      setHistorial({ ...h, sesiones: [...historial.sesiones, ...h.sesiones] });
    } catch (e) { setError(e instanceof Error ? e.message : 'No se pudieron cargar más sesiones.'); }
    finally { setCargandoMas(false); }
  }

  // Por defecto, Máquinas (si usaste alguna); si no, todos.
  const efectivo: Filtro = filtro ?? (ejercicios?.some(e => e.ejercicio.categoria_equipo === 'maquina') ? 'maquina' : 'todos');
  const visibles = (ejercicios ?? []).filter(e => efectivo === 'todos' || e.ejercicio.categoria_equipo === efectivo);
  const meta = perfil?.dias_por_semana;

  return (
    <div className="pantalla stack" style={{ gap: 16 }}>
      <header className="fila" style={{ justifyContent: 'space-between', paddingTop: 8, flexWrap: 'wrap', gap: 8 }}>
        <h1 style={{ fontSize: 24 }}>Mi progreso</h1>
        <Link to="/registrar-pasado" className="btn btn-claro btn-auto"><IconPlus width={18} height={18} /> Registrar entrenamiento pasado</Link>
      </header>
      {error && <Aviso>{error}</Aviso>}
      {!constancia && !error && <p className="muted pulse-latido" style={{ textAlign: 'center', padding: 20 }}>Cargando tu progreso…</p>}

      {constancia && (
        <section className="grid-3 kpis-hoy" aria-label="Constancia">
          <div className="card kpi"><b>{constancia.racha_actual} <IconFlame width={18} height={18} className="icono-en-texto" aria-hidden="true" /></b><span>Racha actual</span><small>Mejor: {constancia.mejor_racha}</small></div>
          <div className="card kpi"><b>{constancia.sesiones_semana}{meta ? `/${meta}` : ''}</b><span>Esta semana</span></div>
          <div className="card kpi"><b>{constancia.sesiones_mes}</b><span>Este mes</span></div>
        </section>
      )}

      {alertas.map(a => (
        <div key={a.titulo} className="aviso aviso-info stack" style={{ gap: 4 }} role="status">
          <b>
            {a.tipo === 'retorno'
              ? <IconRefresh width={16} height={16} className="icono-en-texto" aria-hidden="true" />
              : <IconPause width={16} height={16} className="icono-en-texto" aria-hidden="true" />}{' '}
            {a.titulo}
          </b>
          <span>{a.texto}</span>
          {a.ejercicio_id != null && <Link to={`/progreso/ejercicios/${a.ejercicio_id}`} style={{ fontWeight: 700 }}>Ver su evolución</Link>}
        </div>
      ))}

      {ejercicios && (
        <section className="stack" style={{ gap: 10 }} aria-labelledby="mis-maquinas">
          <h2 id="mis-maquinas" style={{ fontSize: 18 }}>Mis máquinas y pesos</h2>
          {ejercicios.length === 0 ? (
            <div className="card stack" style={{ gap: 6 }}>
              <p style={{ fontSize: 14 }}>Aquí verás cada máquina que uses, con tus pesos y récords.</p>
              <p className="muted" style={{ fontSize: 13.5 }}>Aparecen después de tu primera sesión: marca tus series en la rutina de hoy.</p>
            </div>
          ) : (
            <>
              <div className="chips filtros-progreso" role="group" aria-label="Filtrar por equipo">
                {FILTROS.map(f => (
                  <button key={f.valor} type="button" className="chip" aria-pressed={efectivo === f.valor} onClick={() => setFiltro(f.valor)}>{f.texto}</button>
                ))}
              </div>
              {visibles.length === 0 && <p className="muted" style={{ fontSize: 14 }}>Todavía no hiciste ejercicios de este tipo.</p>}
              <div className="grilla-ejercicios">
                {visibles.map(e => <FilaEjercicio key={e.ejercicio.id} e={e} />)}
              </div>
            </>
          )}
        </section>
      )}

      {historial && (
        <section className="stack" style={{ gap: 10 }} aria-labelledby="mis-sesiones">
          <h2 id="mis-sesiones" style={{ fontSize: 18 }}>Historial de sesiones</h2>
          {historial.total === 0 && <p className="muted" style={{ fontSize: 14 }}>Aún no terminaste ninguna sesión.</p>}
          {historial.sesiones.map(s => (
            <Link key={s.id} to={`/sesion/${s.id}`} className="card fila" style={{ textDecoration: 'none', color: 'inherit', justifyContent: 'space-between', gap: 10 }}>
              <span className="stack" style={{ gap: 3, minWidth: 0 }}>
                <span className="fila" style={{ gap: 8, flexWrap: 'wrap' }}>
                  <b style={{ fontSize: 15 }}>{fechaCorta(s.fecha)} · {s.enfoque}</b>
                  <Insignia tono={ESTADO[s.estado].tono}>{ESTADO[s.estado].texto}</Insignia>
                </span>
                <span className="muted" style={{ fontSize: 12.5 }}>
                  {s.gym_nombre && <><IconMapPin width={12} height={12} /> {s.gym_nombre} · </>}
                  {Math.round(s.duracion_seg / 60)} min · {s.series_hechas}/{s.series_planeadas} series
                  {s.records > 0 && <> · <IconTrophy width={13} height={13} className="icono-en-texto" aria-hidden="true" /> {s.records} {s.records === 1 ? 'récord' : 'récords'}</>}
                </span>
              </span>
              <IconChevronRight width={18} height={18} style={{ flexShrink: 0, color: 'var(--muted)' }} />
            </Link>
          ))}
          {historial.sesiones.length < historial.total && (
            <button className="btn btn-claro" disabled={cargandoMas} onClick={() => void verMas()}>{cargandoMas ? 'Cargando…' : 'Ver más sesiones'}</button>
          )}
        </section>
      )}
    </div>
  );
}

function FilaEjercicio({ e }: { e: EjercicioUsado }) {
  const primera = e.ultima[0];
  const iguales = primera && e.ultima.every(s => s.peso_kg === primera.peso_kg && s.repeticiones === primera.repeticiones);
  const series = `${e.ultima.length} ${e.ultima.length === 1 ? 'serie' : 'series'}`;
  const peso = iguales && primera.peso_kg > 0 ? kg(primera.peso_kg) : null;
  return (
    <Link to={`/progreso/ejercicios/${e.ejercicio.id}`} className="card stack" style={{ gap: 5, textDecoration: 'none', color: 'inherit', overflowWrap: 'anywhere' }}>
      <b style={{ fontSize: 15 }}>{e.ejercicio.nombre}</b>
      <span className="muted" style={{ fontSize: 12.5 }}>
        {e.ejercicio.musculo_principal || EQUIPO[e.ejercicio.categoria_equipo]}
      </span>
      <span style={{ fontSize: 14 }}>
        Última sesión · {fechaCorta(e.ultima_fecha)} ·{' '}
        <b>
          {series}
          {iguales && ` × ${primera.repeticiones} reps`}
          {peso && <> · <span style={{ whiteSpace: 'nowrap' }}>{peso}</span></>}
        </b>
      </span>
      <span className="pill-record"><IconTrophy width={14} height={14} className="icono-en-texto" aria-hidden="true" /> Récord personal · {marca(e.mejor.peso_kg, e.mejor.repeticiones)}</span>
      <LineaPeso s={e.sugerencia} />
      <span className="fila" style={{ gap: 4, color: 'var(--primary)', fontSize: 13, fontWeight: 700 }}>
        Ver historial y evolución <IconChevronRight width={16} height={16} aria-hidden="true" style={{ flexShrink: 0 }} />
      </span>
    </Link>
  );
}
