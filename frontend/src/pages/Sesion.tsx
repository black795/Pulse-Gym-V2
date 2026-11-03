/**
 * Sesión en vivo (Sprint 4): cronómetro (PG-34), registro de series con la "vez pasada" (PG-35), récords (PG-40),
 * descanso con sonido (PG-36), máquina ocupada (PG-29), "me molesta" (PG-22) y el resumen al finalizar (PG-37).
 * La sesión está congelada (PG-30): lo que cambie en el plan o en el gym mientras entrenas no la toca.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { IconAlertTriangle, IconCheck, IconClock, IconMapPin, IconRefresh, IconX } from '../components/Icons';
import { Aviso, Insignia, aNumero } from '../components/UI';
import { lesionesApi, sesionesApi } from '../lib/endpoints';
import { ApiError } from '../lib/http';
import { pitido, preparar } from '../lib/sonido';
import type { MotivoReemplazo, OpcionesReemplazo, SesionEjercicio, SesionVivo, Zona } from '../lib/tipos';
import { EQUIPO, descanso, repeticiones } from './Plan';

const SERIES_EXTRA = 3; // el backend acepta hasta 3 series más que las del plan

/** 1925 → "32:05"; 3725 → "1:02:05". */
export function reloj(seg: number) {
  const s = Math.max(0, Math.floor(seg));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
  const mm = String(m).padStart(h ? 2 : 1, '0'), ss = String(r).padStart(2, '0');
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}
const kg = (n: number) => `${n.toLocaleString('es', { maximumFractionDigits: 1 })} kg`;
const marca = (peso: number, reps: number) => (peso > 0 ? `${kg(peso)} × ${reps}` : `${reps} reps`);

export default function Sesion() {
  const { id } = useParams();
  const [sesion, setSesion] = useState<SesionVivo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    sesionesApi.ver(Number(id)).then(setSesion).catch(e => setError(e instanceof Error ? e.message : 'No se pudo cargar la sesión.'));
  }, [id]);

  if (error) return <div className="app-frame pantalla-sin-nav stack"><Aviso>{error}</Aviso><Link to="/" className="btn">Volver a Hoy</Link></div>;
  if (!sesion) return <div className="app-frame pantalla-sin-nav"><p className="muted pulse-latido" style={{ textAlign: 'center', padding: 40 }}>Cargando tu sesión…</p></div>;
  return sesion.estado === 'en_curso' ? <EnVivo sesion={sesion} setSesion={setSesion} /> : <Resumen sesion={sesion} />;
}

// ---------------- En vivo ----------------
function EnVivo({ sesion, setSesion }: { sesion: SesionVivo; setSesion: (s: SesionVivo) => void }) {
  const nav = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [descansoFin, setDescansoFin] = useState<{ fin: number; total: number } | null>(null);
  const [hoja, setHoja] = useState<{ se: SesionEjercicio; motivo: MotivoReemplazo } | null>(null);
  const [confirmar, setConfirmar] = useState<'finalizar' | 'descartar' | null>(null);

  // PG-34: el cronómetro usa la hora del servidor (no depende de si el reloj del celular está mal).
  const base = useRef({ inicio: Date.parse(sesion.inicio_at), servidor: Date.parse(sesion.ahora), local: Date.now() });
  const transcurrido = useTick(() => (Date.now() - base.current.local + base.current.servidor - base.current.inicio) / 1000);

  const activo = sesion.ejercicios.find(e => !e.cerrado && e.hechas.length < e.series);
  const pct = sesion.series_planeadas ? Math.round((100 * sesion.series_hechas) / sesion.series_planeadas) : 0;

  async function accion(fn: () => Promise<SesionVivo>) {
    setError(null); setOcupado(true);
    try { setSesion(await fn()); return true; }
    catch (e) {
      if (e instanceof ApiError && e.codigo === 'sesion_terminada') { setSesion(await sesionesApi.ver(sesion.id)); return false; }
      setError(e instanceof Error ? e.message : 'No se pudo guardar. Intenta de nuevo.');
      return false;
    } finally { setOcupado(false); }
  }

  async function marcar(se: SesionEjercicio, numero: number, peso: number, reps: number) {
    preparar(); // el toque "desbloquea" el sonido del fin del descanso
    const ok = await accion(() => sesionesApi.serie(sesion.id, se.id, numero, { peso_kg: peso, repeticiones: reps }));
    if (ok) setDescansoFin({ fin: Date.now() + se.descanso_seg * 1000, total: se.descanso_seg }); // PG-36
  }

  async function finalizar() {
    setConfirmar(null);
    setDescansoFin(null);
    await accion(() => sesionesApi.finalizar(sesion.id));
  }

  async function descartar() {
    setConfirmar(null); setOcupado(true);
    try { await sesionesApi.descartar(sesion.id); nav('/', { replace: true }); }
    catch (e) { setError(e instanceof Error ? e.message : 'No se pudo descartar.'); setOcupado(false); }
  }

  const faltan = sesion.series_planeadas - sesion.series_hechas;

  return (
    <div className="app-frame sesion-vivo">
      <header className="sesion-cabecera">
        <div className="fila" style={{ justifyContent: 'space-between' }}>
          <div className="stack" style={{ gap: 2 }}>
            <span className="sesion-estado"><span aria-hidden="true">●</span> Sesión en curso</span>
            <span className="cronometro" role="timer" aria-label="Tiempo de entrenamiento">{reloj(transcurrido)}</span>
          </div>
          <button className="btn btn-peligro btn-auto" style={{ minHeight: 44 }} disabled={ocupado} onClick={() => setConfirmar('finalizar')}>
            Finalizar rutina
          </button>
        </div>
        <div className="metricas-vivo">
          <div><b>{sesion.series_hechas}/{sesion.series_planeadas}</b><span>Series ({pct}%)</span></div>
          <div><b>{kg(sesion.volumen_kg)}</b><span>Volumen</span></div>
          <div><b className="recortar">{sesion.gym_nombre ?? 'Sin gym'}</b><span>{sesion.enfoque}</span></div>
        </div>
        <div className="barra-subida" style={{ background: '#22332a' }} aria-hidden="true"><span style={{ width: `${pct}%`, background: 'var(--neon)' }} /></div>
      </header>

      <main className="pantalla-sin-nav stack" style={{ gap: 12, paddingTop: 16, paddingBottom: descansoFin ? 150 : 40 }}>
        {error && <Aviso>{error}</Aviso>}
        {sesion.ejercicios.map(se => (
          <TarjetaEjercicio key={se.id} se={se} activo={se.id === activo?.id} ocupado={ocupado}
            onMarcar={(n, p, r) => void marcar(se, n, p, r)}
            onDeshacer={n => void accion(() => sesionesApi.borrarSerie(sesion.id, se.id, n))}
            onReemplazo={motivo => setHoja({ se, motivo })} />
        ))}
        {!activo && <Aviso tipo="ok">¡Hiciste todas las series! Toca <b>Finalizar rutina</b> para guardar tu sesión.</Aviso>}
        <button className="btn-texto" style={{ alignSelf: 'center', color: 'var(--muted)' }} disabled={ocupado} onClick={() => setConfirmar('descartar')}>
          Empecé por error · Descartar esta sesión
        </button>
      </main>

      {descansoFin && <Descanso {...descansoFin} onCambiar={d => setDescansoFin(x => x && { ...x, fin: x.fin + d * 1000, total: Math.max(0, x.total + d) })}
        onTerminar={() => setDescansoFin(null)} />}

      {hoja && <HojaReemplazo sesionId={sesion.id} se={hoja.se} motivo={hoja.motivo} onCerrar={() => setHoja(null)}
        onListo={s => { setSesion(s); setHoja(null); }} />}

      {confirmar && (
        <div className="velo" role="dialog" aria-modal="true" aria-labelledby="confirmar-titulo" onClick={() => setConfirmar(null)}>
          <div className="hoja stack" style={{ gap: 14 }} onClick={e => e.stopPropagation()}>
            {confirmar === 'finalizar' ? (
              <>
                <h2 id="confirmar-titulo" style={{ fontSize: 18 }}>¿Terminar la rutina?</h2>
                <p className="muted" style={{ fontSize: 14 }}>
                  {faltan > 0 ? `Te faltan ${faltan} ${faltan === 1 ? 'serie' : 'series'}. Lo que marcaste se guarda igual en tu historial.` : 'Marcaste todas las series. ¡Buen trabajo!'}
                </p>
                <button className="btn" onClick={() => void finalizar()}>Sí, finalizar</button>
              </>
            ) : (
              <>
                <h2 id="confirmar-titulo" style={{ fontSize: 18 }}>¿Descartar esta sesión?</h2>
                <p className="muted" style={{ fontSize: 14 }}>Se borra todo lo que marcaste en ella y no queda en tu historial.</p>
                <button className="btn btn-peligro" onClick={() => void descartar()}>Sí, descartar</button>
              </>
            )}
            <button className="btn btn-claro" onClick={() => setConfirmar(null)}>Seguir entrenando</button>
          </div>
        </div>
      )}
    </div>
  );
}

/** Repite `calcular` cada medio segundo (para relojes). */
function useTick(calcular: () => number) {
  const [valor, setValor] = useState(calcular);
  const ref = useRef(calcular);
  ref.current = calcular;
  useEffect(() => {
    const t = setInterval(() => setValor(ref.current()), 500);
    return () => clearInterval(t);
  }, []);
  return valor;
}

// ---------------- Tarjeta de ejercicio y tabla de series (PG-35, PG-40) ----------------
function TarjetaEjercicio({ se, activo, ocupado, onMarcar, onDeshacer, onReemplazo }: {
  se: SesionEjercicio; activo: boolean; ocupado: boolean; onMarcar: (numero: number, peso: number, reps: number) => void;
  onDeshacer: (numero: number) => void; onReemplazo: (motivo: MotivoReemplazo) => void;
}) {
  const [extra, setExtra] = useState(0);
  const sinPeso = se.ejercicio.categoria_equipo === 'sin_equipo';
  const maxHechas = Math.max(0, ...se.hechas.map(h => h.numero));
  const filas = se.cerrado ? se.series : Math.min(se.series + SERIES_EXTRA, Math.max(se.series, maxHechas) + extra);
  const terminado = !se.cerrado && se.hechas.length >= se.series;

  return (
    <article className={`card stack serie-tarjeta${activo ? ' activa' : ''}${se.cerrado ? ' cerrada' : ''}`} style={{ gap: 10 }} aria-current={activo ? 'step' : undefined}>
      <div className="fila" style={{ alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div className="fila" style={{ alignItems: 'flex-start', minWidth: 0 }}>
          <span className="ejercicio-orden">{terminado ? <IconCheck width={16} height={16} /> : se.orden}</span>
          <div className="stack" style={{ gap: 3, minWidth: 0 }}>
            <b style={{ fontSize: 15.5 }}>{se.ejercicio.nombre}</b>
            <span className="muted" style={{ fontSize: 12.5 }}>
              {se.ejercicio.maquinas.length ? se.ejercicio.maquinas.join(' o ') : EQUIPO[se.ejercicio.categoria_equipo]} · {se.series} × {repeticiones(se.reps_min, se.reps_max)} · descanso {descanso(se.descanso_seg)}
            </span>
            <div className="fila" style={{ gap: 6, flexWrap: 'wrap' }}>
              {se.cerrado && <Insignia tono="neutro">Reemplazado</Insignia>}
              {se.motivo === 'maquina_ocupada' && <Insignia tono="aviso">Máquina ocupada</Insignia>}
              {se.motivo === 'molestia_dolor' && <Insignia tono="peligro">Por molestia</Insignia>}
              {(se.motivo === 'adaptado_gym' || se.motivo === 'sin_equipo') && <Insignia tono="aviso">Adaptado a este gym</Insignia>}
              {se.precaucion && <Insignia tono="peligro">Con precaución</Insignia>}
            </div>
          </div>
        </div>
      </div>

      {!se.cerrado && !terminado && (
        <div className="fila" style={{ gap: 8 }}>
          {se.ejercicio.categoria_equipo !== 'sin_equipo' && (
            <button className="chip chip-ocupada" disabled={ocupado} onClick={() => onReemplazo('maquina_ocupada')}><IconClock width={15} height={15} /> Máquina ocupada</button>
          )}
          <button className="chip chip-molesta" disabled={ocupado} onClick={() => onReemplazo('molestia_dolor')}><IconAlertTriangle width={15} height={15} /> Me molesta</button>
        </div>
      )}

      {se.nota && se.reemplaza && <p className="cambio-nota">En lugar de <b>{se.reemplaza.nombre}</b>. {se.nota}</p>}
      {se.mejor && <span className="pill-record">🏆 Tu récord: {marca(se.mejor.peso_kg, se.mejor.repeticiones)}</span>}

      <div className="tabla-series" role="table" aria-label={`Series de ${se.ejercicio.nombre}`}>
        <div className="tabla-series-fila cabeza" role="row">
          <span role="columnheader">Serie</span><span role="columnheader">Vez pasada</span>
          <span role="columnheader">{sinPeso ? 'Kg extra' : 'Kg'}</span><span role="columnheader">Reps</span><span role="columnheader"><span className="sr-only">Listo</span></span>
        </div>
        {Array.from({ length: filas }, (_, i) => i + 1).map(n => (
          <FilaSerie key={n} se={se} numero={n} ocupado={ocupado || se.cerrado} sinPeso={sinPeso}
            onMarcar={(p, r) => onMarcar(n, p, r)} onDeshacer={() => onDeshacer(n)} />
        ))}
      </div>
      {!se.cerrado && filas < se.series + SERIES_EXTRA && se.hechas.length >= se.series && (
        <button className="btn-texto" style={{ alignSelf: 'flex-start' }} onClick={() => setExtra(x => x + 1)}>+ Serie extra</button>
      )}
    </article>
  );
}

function FilaSerie({ se, numero, ocupado, sinPeso, onMarcar, onDeshacer }: {
  se: SesionEjercicio; numero: number; ocupado: boolean; sinPeso: boolean;
  onMarcar: (peso: number, reps: number) => void; onDeshacer: () => void;
}) {
  const hecha = se.hechas.find(h => h.numero === numero);
  const antes = se.anterior.find(a => a.numero === numero) ?? se.anterior.at(-1);
  // Se propone lo último que hiciste hoy en este ejercicio; si no, lo de la vez pasada; si no, el máximo del rango.
  const previa = [...se.hechas].filter(h => h.numero < numero).at(-1);
  const pesoSugerido = previa?.peso_kg ?? antes?.peso_kg ?? (sinPeso ? 0 : undefined);
  const repsSugeridas = previa?.repeticiones ?? antes?.repeticiones ?? se.reps_max;
  const [peso, setPeso] = useState('');
  const [reps, setReps] = useState('');

  if (hecha) {
    return (
      <div className="tabla-series-fila hecha" role="row">
        <span className="num" role="cell">{numero}</span>
        <span className="muted" role="cell">{antes ? marca(antes.peso_kg, antes.repeticiones) : '—'}</span>
        <b role="cell">{hecha.peso_kg.toLocaleString('es')}</b>
        <b role="cell">{hecha.repeticiones}</b>
        <span role="cell">
          <button className="boton-listo hecho" disabled={ocupado} onClick={onDeshacer} aria-label={`Deshacer serie ${numero}`} title="Deshacer">
            <IconCheck width={18} height={18} />
          </button>
        </span>
        {hecha.es_record && <span className="insignia-record" role="cell">🏆 ¡Nuevo récord!</span>}
      </div>
    );
  }

  const pesoFinal = peso.trim() === '' ? pesoSugerido : aNumero(peso);
  const repsFinal = reps.trim() === '' ? repsSugeridas : aNumero(reps);
  const valido = pesoFinal !== undefined && pesoFinal >= 0 && pesoFinal <= 500 && repsFinal !== undefined && Number.isInteger(repsFinal) && repsFinal >= 1 && repsFinal <= 100;
  return (
    <form className="tabla-series-fila" role="row" onSubmit={e => { e.preventDefault(); if (valido) onMarcar(pesoFinal!, repsFinal!); }}>
      <span className="num" role="cell">{numero}</span>
      <span className="muted" role="cell">{antes ? marca(antes.peso_kg, antes.repeticiones) : '—'}</span>
      <span role="cell">
        <input className="input-serie" inputMode="decimal" aria-label={`Kilos de la serie ${numero}`} value={peso}
          placeholder={pesoSugerido !== undefined ? String(pesoSugerido) : 'kg'} onChange={e => setPeso(e.target.value)} disabled={ocupado} />
      </span>
      <span role="cell">
        <input className="input-serie" inputMode="numeric" aria-label={`Repeticiones de la serie ${numero}`} value={reps}
          placeholder={String(repsSugeridas)} onChange={e => setReps(e.target.value)} disabled={ocupado} />
      </span>
      <span role="cell">
        <button type="submit" className="boton-listo" disabled={ocupado || !valido} aria-label={`Marcar serie ${numero} como lista`}>
          <IconCheck width={18} height={18} />
        </button>
      </span>
    </form>
  );
}

// ---------------- PG-36: descanso con sonido ----------------
function Descanso({ fin, total, onCambiar, onTerminar }: { fin: number; total: number; onCambiar: (seg: number) => void; onTerminar: () => void }) {
  const restante = useTick(() => (fin - Date.now()) / 1000);
  const terminar = useRef(onTerminar);
  terminar.current = onTerminar;
  const terminado = restante <= 0;

  // Al llegar a cero suena una vez y la barra se va sola a los 4 s (con +15 s vuelve a contar).
  useEffect(() => {
    if (!terminado) return;
    pitido();
    const t = setTimeout(() => terminar.current(), 4000);
    return () => clearTimeout(t);
  }, [terminado]);

  const pct = total > 0 ? Math.min(100, Math.max(0, 100 * (1 - restante / total))) : 100;
  return (
    <section className="descanso-flotante" role="timer" aria-live="polite" aria-label="Descanso">
      <div className="fila" style={{ justifyContent: 'space-between' }}>
        <div className="stack" style={{ gap: 0 }}>
          <span style={{ fontSize: 12, color: '#8fad99', fontWeight: 700 }}>{terminado ? '¡A la siguiente serie!' : 'Descanso'}</span>
          <span className="cronometro" style={{ fontSize: 28 }}>{reloj(Math.ceil(Math.max(0, restante)))} <small>/ {reloj(total)}</small></span>
        </div>
        <span style={{ fontSize: 12, color: '#8fad99' }}>🔊 Sonará al terminar</span>
      </div>
      <div className="barra-subida" style={{ background: '#22332a' }}><span style={{ width: `${pct}%`, background: 'var(--neon)' }} /></div>
      <div className="grid-3">
        <button className="btn btn-claro" onClick={() => onCambiar(-15)} disabled={terminado}>−15 s</button>
        <button className="btn btn-claro" onClick={() => onCambiar(15)}>+15 s</button>
        <button className="btn btn-neon" onClick={onTerminar}>{terminado ? 'Listo' : 'Saltar'}</button>
      </div>
    </section>
  );
}

// ---------------- PG-29 y PG-22: hoja de reemplazo ----------------
function HojaReemplazo({ sesionId, se, motivo, onCerrar, onListo }: {
  sesionId: number; se: SesionEjercicio; motivo: MotivoReemplazo; onCerrar: () => void; onListo: (s: SesionVivo) => void;
}) {
  const [zonas, setZonas] = useState<Zona[]>([]);
  const [zona, setZona] = useState<string | null>(null);
  const [datos, setDatos] = useState<OpcionesReemplazo | null>(null);
  const [elegido, setElegido] = useState<number | null>(null);
  const [guardar, setGuardar] = useState(true);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async (z?: string) => {
    setCargando(true); setError(null); setDatos(null); setElegido(null);
    try {
      const d = await sesionesApi.reemplazos(sesionId, se.id, motivo, z);
      setDatos(d);
      setElegido(d.opciones[0]?.id ?? null); // la primera es la recomendada
    } catch (e) { setError(e instanceof Error ? e.message : 'No se pudieron cargar las opciones.'); }
    finally { setCargando(false); }
  }, [sesionId, se.id, motivo]);

  useEffect(() => {
    if (motivo === 'maquina_ocupada') void cargar();
    else lesionesApi.zonas().then(setZonas).catch(() => setError('No se pudieron cargar las zonas.'));
  }, [motivo, cargar]);

  async function confirmar() {
    if (elegido == null) return;
    setCargando(true); setError(null);
    try {
      onListo(await sesionesApi.reemplazar(sesionId, se.id, {
        ejercicio_id: elegido, motivo, zona: zona ?? undefined,
        guardar_lesion: motivo === 'molestia_dolor' && !!datos?.puede_guardar_lesion && guardar,
      }));
    } catch (e) { setError(e instanceof Error ? e.message : 'No se pudo cambiar el ejercicio.'); setCargando(false); }
  }

  const NIVEL = { 1: 'Otra máquina libre de tu gym', 2: 'Peso libre', 3: 'Sin equipo' } as Record<number, string>;
  return (
    <div className="velo" role="dialog" aria-modal="true" aria-labelledby="hoja-reemplazo" onClick={onCerrar}>
      <div className="hoja stack" style={{ gap: 14 }} onClick={e => e.stopPropagation()}>
        <div className="fila" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <h2 id="hoja-reemplazo" style={{ fontSize: 18 }}>
            {motivo === 'maquina_ocupada' ? `¿${se.ejercicio.nombre} está ocupada? Elige tu reemplazo para hoy` : '¿Qué zona te molesta en este ejercicio?'}
          </h2>
          <button className="btn-texto" onClick={onCerrar} aria-label="Cerrar"><IconX /></button>
        </div>
        <p className="muted" style={{ fontSize: 13.5 }}>Solo cambia la sesión de hoy; tu plan semanal no se altera.</p>

        {motivo === 'molestia_dolor' && (
          <div className="chips">
            {zonas.map(z => (
              <button key={z.codigo} type="button" className="chip" aria-pressed={zona === z.codigo} disabled={cargando}
                onClick={() => { setZona(z.codigo); void cargar(z.codigo); }}>{z.nombre}</button>
            ))}
          </div>
        )}

        {error && <Aviso>{error}</Aviso>}
        {cargando && !datos && <p className="muted pulse-latido">Buscando opciones seguras…</p>}
        {datos?.aviso && <Aviso tipo="info">{datos.aviso}</Aviso>}

        {datos && datos.opciones.length > 0 && (
          <>
            {motivo === 'molestia_dolor' && <b style={{ fontSize: 14 }}>Te proponemos algo que no carga esa zona:</b>}
            <div className="opciones">
              {datos.opciones.map((o, i) => (
                <button key={o.id} type="button" className="opcion stack" style={{ gap: 2 }} aria-pressed={elegido === o.id} onClick={() => setElegido(o.id)}>
                  <span className="fila" style={{ gap: 6, flexWrap: 'wrap' }}>
                    <b>{o.nombre}</b>
                    {i === 0 && <Insignia tono="ok">Recomendado</Insignia>}
                    {o.precaucion && <Insignia tono="peligro">Con precaución</Insignia>}
                  </span>
                  <span className="muted" style={{ fontSize: 12.5, fontWeight: 500 }}>
                    {NIVEL[o.nivel_busqueda]}{o.maquinas.length ? ` · ${o.maquinas.map(m => m.nombre).join(' o ')}` : ''}
                    {o.categoria_equipo !== 'sin_equipo' ? ' · empieza con un peso prudente' : ''}
                  </span>
                </button>
              ))}
            </div>
            {motivo === 'molestia_dolor' && datos.puede_guardar_lesion && (
              <label className="fila" style={{ fontSize: 14, alignItems: 'flex-start', cursor: 'pointer' }}>
                <input type="checkbox" checked={guardar} onChange={e => setGuardar(e.target.checked)} style={{ width: 20, height: 20, marginTop: 2 }} />
                <span>Guardar esta molestia en mi perfil de lesiones para proteger mis próximas rutinas</span>
              </label>
            )}
            <button className="btn" disabled={cargando || elegido == null} onClick={() => void confirmar()}>
              <IconRefresh width={18} height={18} /> Cambiar por este ejercicio
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------- PG-37: resumen al finalizar ----------------
function Resumen({ sesion }: { sesion: SesionVivo }) {
  const r = sesion.resumen!;
  const completa = r.estado === 'completa';
  return (
    <div className="app-frame sesion-vivo">
      <main className="pantalla-sin-nav stack" style={{ gap: 16 }}>
        <section className={`medalla ${completa ? 'completa' : 'parcial'}`}>
          <span style={{ fontSize: 40 }} aria-hidden="true">{completa ? '🏅' : '📝'}</span>
          <h1 style={{ fontSize: 22 }}>{completa ? '¡Sesión completa!' : 'Sesión parcial guardada en tu historial'}</h1>
          <p style={{ fontSize: 14 }}>{r.mensaje}</p>
          {completa && <span className="etiqueta-neon">CUENTA PARA TU ASISTENCIA</span>}
        </section>

        <div className="grid-2">
          <div className="card stack" style={{ gap: 2 }}>
            <span className="muted" style={{ fontSize: 12.5 }}>Duración</span>
            <b style={{ fontSize: 20 }}>{reloj(r.duracion_seg)}</b>
            <span className="muted" style={{ fontSize: 12 }}>Estimado: {Math.round(r.duracion_estimada_seg / 60)} min</span>
          </div>
          <div className="card stack" style={{ gap: 2 }}>
            <span className="muted" style={{ fontSize: 12.5 }}>Series</span>
            <b style={{ fontSize: 20 }}>{r.series_hechas}/{r.series_planeadas}</b>
            <span className="muted" style={{ fontSize: 12 }}>{r.porcentaje}% de lo planeado</span>
          </div>
          <div className="card stack" style={{ gap: 2 }}>
            <span className="muted" style={{ fontSize: 12.5 }}>Volumen</span>
            <b style={{ fontSize: 20 }}>{kg(r.volumen_kg)}</b>
            <span className="muted" style={{ fontSize: 12 }}>kilos × repeticiones</span>
          </div>
          <div className="card stack" style={{ gap: 2 }}>
            <span className="muted" style={{ fontSize: 12.5 }}>Récords</span>
            <b style={{ fontSize: 20 }}>{r.records.length} 🏆</b>
            <span className="muted" style={{ fontSize: 12 }}>{sesion.enfoque}</span>
          </div>
        </div>

        {r.records.length > 0 && (
          <section className="card stack" style={{ gap: 8 }}>
            <h2 style={{ fontSize: 16 }}>Nuevos récords personales</h2>
            {r.records.map((x, i) => (
              <div key={i} className="fila" style={{ justifyContent: 'space-between', fontSize: 14 }}>
                <span>{x.ejercicio}</span><b>{marca(x.peso_kg, x.repeticiones)}</b>
              </div>
            ))}
          </section>
        )}

        <section className="card stack" style={{ gap: 8 }}>
          <h2 style={{ fontSize: 16 }}>Lo que hiciste</h2>
          {sesion.ejercicios.map(e => (
            <div key={e.id} className="fila" style={{ justifyContent: 'space-between', fontSize: 14, gap: 12 }}>
              <span style={{ minWidth: 0 }}>{e.ejercicio.nombre}</span>
              <span className="muted" style={{ flexShrink: 0 }}>{e.hechas.length}/{e.series} series</span>
            </div>
          ))}
          {sesion.gym_nombre && <span className="muted fila" style={{ fontSize: 12.5, gap: 4 }}><IconMapPin width={14} height={14} /> {sesion.gym_nombre}</span>}
        </section>

        <Link to="/" className="btn">Volver a Hoy</Link>
      </main>
    </div>
  );
}
