/**
 * PG-39 "Registrar entrenamiento pasado" (Sprint 5): entrenaste y olvidaste anotarlo. Eliges cuándo (hasta 7 días
 * atrás), qué día de tu plan hiciste y en qué gym; ves los ejercicios de ese día con el peso sugerido ya escrito y
 * corriges lo que hiciste. Queda en tu historial como sesión "manual".
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { IconCheck } from '../components/Icons';
import { Aviso, Volver, aNumero } from '../components/UI';
import { planApi, sesionesApi } from '../lib/endpoints';
import type { DiaSemana, EjercicioHoy, Hoy, RutinaDia } from '../lib/tipos';
import { DIAS, EQUIPO, repeticiones } from './Plan';

interface Fila { peso: string; reps: string; hecha: boolean }
const DIAS_ATRAS = 7;

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
function fechasPosibles() {
  return Array.from({ length: DIAS_ATRAS + 1 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const texto = i === 0 ? 'Hoy' : i === 1 ? 'Ayer' : d.toLocaleDateString('es', { weekday: 'short', day: 'numeric' });
    return { valor: iso(d), texto, dia: DIAS[(d.getDay() + 6) % 7].valor };
  });
}

function filasDe(e: EjercicioHoy): Fila[] {
  const sinPeso = e.ejercicio.categoria_equipo === 'sin_equipo';
  const peso = e.peso_sugerido?.peso_kg ?? (sinPeso ? 0 : null);
  const reps = e.peso_sugerido?.reps ?? e.reps_max;
  return Array.from({ length: e.series }, () => ({ peso: peso == null ? '' : String(peso), reps: String(reps), hecha: true }));
}

export default function RegistrarPasado() {
  const nav = useNavigate();
  const fechas = fechasPosibles();
  const [fecha, setFecha] = useState(fechas[1].valor); // ayer
  const [diasPlan, setDiasPlan] = useState<RutinaDia[] | null>(null);
  const [dia, setDia] = useState<DiaSemana | null>(null);
  const [gymId, setGymId] = useState<number | null>(null);
  const [hoy, setHoy] = useState<Hoy | null>(null);
  const [filas, setFilas] = useState<Record<number, Fila[]>>({});
  const [cargando, setCargando] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // El día del plan que corresponde a esa fecha (si no toca ninguno, el primero del plan).
  function diaPara(f: string, dias: RutinaDia[]) {
    const semana = fechas.find(x => x.valor === f)?.dia;
    return dias.find(d => d.dia === semana)?.dia ?? dias[0]?.dia ?? null;
  }

  useEffect(() => {
    planApi.ver().then(e => {
      const dias = e.plan?.dias ?? [];
      setDiasPlan(dias);
      setDia(diaPara(fecha, dias));
    }).catch(e => setError(e instanceof Error ? e.message : 'No se pudo cargar tu plan.'));
  }, []); // solo al entrar: después el día lo cambia el usuario

  useEffect(() => {
    if (!dia) return;
    setCargando(true); setError(null);
    planApi.hoy({ dia, gym_id: gymId ?? undefined }).then(h => {
      setHoy(h);
      setFilas(Object.fromEntries((h.sesion?.ejercicios ?? []).map(e => [e.ejercicio.id, filasDe(e)])));
    }).catch(e => setError(e instanceof Error ? e.message : 'No se pudo cargar ese día.')).finally(() => setCargando(false));
  }, [dia, gymId]);

  function cambiar(eid: number, i: number, cambio: Partial<Fila>) {
    setFilas(f => ({ ...f, [eid]: f[eid].map((x, k) => (k === i ? { ...x, ...cambio } : x)) }));
  }

  const ejercicios = hoy?.sesion?.ejercicios ?? [];
  const marcadas = ejercicios.flatMap(e => (filas[e.ejercicio.id] ?? []).filter(f => f.hecha));
  const validas = marcadas.every(f => {
    const p = aNumero(f.peso), r = aNumero(f.reps);
    return p !== undefined && p >= 0 && p <= 500 && r !== undefined && Number.isInteger(r) && r >= 1 && r <= 100;
  });

  async function guardar() {
    if (!dia || !marcadas.length || !validas) return;
    setGuardando(true); setError(null);
    try {
      const s = await sesionesApi.registrarPasada({
        fecha, dia, gym_id: hoy?.sesion?.gym_id ?? undefined,
        ejercicios: ejercicios.map(e => ({
          ejercicio_id: e.ejercicio.id,
          series: (filas[e.ejercicio.id] ?? []).filter(f => f.hecha).map(f => ({ peso_kg: aNumero(f.peso)!, repeticiones: aNumero(f.reps)! })),
        })).filter(e => e.series.length > 0),
      });
      nav(`/sesion/${s.id}`, { replace: true });
    } catch (e) { setError(e instanceof Error ? e.message : 'No se pudo guardar.'); setGuardando(false); }
  }

  return (
    <div className="pantalla stack" style={{ gap: 16 }}>
      <Volver a="/progreso" texto="Mi progreso" />
      <header className="stack" style={{ gap: 4 }}>
        <h1 style={{ fontSize: 22 }}>Registrar entrenamiento pasado</h1>
        <p className="muted" style={{ fontSize: 14 }}>¿Entrenaste y olvidaste anotarlo? Cuéntanos qué hiciste (hasta {DIAS_ATRAS} días atrás).</p>
      </header>
      {error && <Aviso>{error}</Aviso>}
      {diasPlan && diasPlan.length === 0 && <Aviso tipo="info">Primero arma tu plan semanal.</Aviso>}

      {diasPlan && diasPlan.length > 0 && (
        <section className="card stack" style={{ gap: 12 }}>
          <div className="stack" style={{ gap: 6 }}>
            <b style={{ fontSize: 14 }}>¿Cuándo?</b>
            <div className="chips" role="group" aria-label="Fecha">
              {fechas.map(f => (
                <button key={f.valor} type="button" className="chip" aria-pressed={fecha === f.valor}
                  onClick={() => { setFecha(f.valor); setDia(diaPara(f.valor, diasPlan)); }}>{f.texto}</button>
              ))}
            </div>
          </div>
          <div className="stack" style={{ gap: 6 }}>
            <b style={{ fontSize: 14 }}>¿Qué día de tu plan hiciste?</b>
            <div className="chips" role="group" aria-label="Día del plan">
              {diasPlan.map(d => (
                <button key={d.dia} type="button" className="chip" aria-pressed={dia === d.dia} onClick={() => setDia(d.dia)}>
                  {DIAS.find(x => x.valor === d.dia)?.corto} · {d.enfoque.split(':')[0]}
                </button>
              ))}
            </div>
          </div>
          {hoy && hoy.gyms.length > 1 && (
            <div className="stack" style={{ gap: 6 }}>
              <b style={{ fontSize: 14 }}>¿En qué gym?</b>
              <div className="chips" role="group" aria-label="Gym">
                {hoy.gyms.map(g => (
                  <button key={g.id} type="button" className="chip" aria-pressed={(hoy.sesion?.gym_id ?? gymId) === g.id} onClick={() => setGymId(g.id)}>{g.nombre}</button>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {cargando && <p className="muted pulse-latido" style={{ textAlign: 'center' }}>Cargando los ejercicios…</p>}
      {hoy?.requiere_elegir_gym && !cargando && <Aviso tipo="info">Elige en qué gym entrenaste.</Aviso>}

      {hoy?.sesion && !cargando && (
        <>
          <p className="muted" style={{ fontSize: 13.5 }}>
            Ya escribimos el peso sugerido y las repeticiones del plan: corrige lo que hiciste y desmarca las series que no hiciste.
          </p>
          {ejercicios.map(e => (
            <article key={e.ejercicio.id} className="card stack" style={{ gap: 8 }}>
              <div className="stack" style={{ gap: 2 }}>
                <b style={{ fontSize: 15 }}>{e.orden}. {e.ejercicio.nombre}</b>
                <span className="muted" style={{ fontSize: 12.5 }}>
                  {e.ejercicio.maquinas.length ? e.ejercicio.maquinas.join(' o ') : EQUIPO[e.ejercicio.categoria_equipo]} · {e.series} × {repeticiones(e.reps_min, e.reps_max)}
                </span>
              </div>
              <div className="tabla-series" role="table" aria-label={`Series de ${e.ejercicio.nombre}`}>
                <div className="tabla-series-fila cabeza pasada" role="row">
                  <span role="columnheader">Serie</span><span role="columnheader">{e.ejercicio.categoria_equipo === 'sin_equipo' ? 'Kg extra' : 'Kg'}</span>
                  <span role="columnheader">Reps</span><span role="columnheader">La hice</span>
                </div>
                {(filas[e.ejercicio.id] ?? []).map((f, i) => (
                  <div key={i} className={`tabla-series-fila pasada${f.hecha ? '' : ' omitida'}`} role="row">
                    <span className="num" role="cell">{i + 1}</span>
                    <span role="cell"><input className="input-serie" inputMode="decimal" value={f.peso} placeholder="kg" disabled={!f.hecha}
                      aria-label={`Kilos de la serie ${i + 1}`} onChange={ev => cambiar(e.ejercicio.id, i, { peso: ev.target.value })} /></span>
                    <span role="cell"><input className="input-serie" inputMode="numeric" value={f.reps} disabled={!f.hecha}
                      aria-label={`Repeticiones de la serie ${i + 1}`} onChange={ev => cambiar(e.ejercicio.id, i, { reps: ev.target.value })} /></span>
                    <span role="cell">
                      <button type="button" className={`boton-listo${f.hecha ? ' hecho' : ''}`} aria-pressed={f.hecha}
                        aria-label={`Serie ${i + 1} ${f.hecha ? 'hecha' : 'no hecha'}`} onClick={() => cambiar(e.ejercicio.id, i, { hecha: !f.hecha })}>
                        <IconCheck width={18} height={18} />
                      </button>
                    </span>
                  </div>
                ))}
              </div>
            </article>
          ))}
          {!validas && <Aviso>Revisa los números: peso de 0 a 500 kg y repeticiones enteras de 1 a 100.</Aviso>}
          <button className="btn" disabled={guardando || !marcadas.length || !validas} onClick={() => void guardar()}>
            {guardando ? 'Guardando…' : `Guardar ${marcadas.length} ${marcadas.length === 1 ? 'serie' : 'series'}`}
          </button>
        </>
      )}
    </div>
  );
}
