/**
 * Evolución de una máquina o ejercicio que ya hiciste (Sprint 5): peso máximo por sesión con tus récords (PG-40),
 * el peso para la próxima vez (PG-41), si estás estancado (PG-43) y cada sesión con sus series.
 */
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import { IconMapPin } from '../components/Icons';
import { kg, PillPeso } from '../components/PesoSugerido';
import { Aviso, Volver } from '../components/UI';
import { progresoApi } from '../lib/endpoints';
import type { EjercicioDetalle, VezEjercicio } from '../lib/tipos';
import { EQUIPO } from './Plan';
import { fechaCorta, marca } from './Progreso';

export default function ProgresoEjercicio() {
  const { id } = useParams();
  const [d, setD] = useState<EjercicioDetalle | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    progresoApi.ejercicio(Number(id)).then(setD).catch(e => setError(e instanceof Error ? e.message : 'No se pudo cargar.'));
  }, [id]);

  if (error) return <div className="pantalla stack"><Volver a="/progreso" texto="Mi progreso" /><Aviso>{error}</Aviso></div>;
  if (!d) return <div className="pantalla"><p className="muted pulse-latido" style={{ textAlign: 'center', padding: 40 }}>Cargando…</p></div>;

  const cambio = d.peso_actual_kg - d.peso_inicial_kg;
  const conPeso = d.historial.some(v => v.peso_max_kg > 0);
  return (
    <div className="pantalla stack" style={{ gap: 16 }}>
      <Volver a="/progreso" texto="Mi progreso" />
      <header className="stack" style={{ gap: 4 }}>
        <h1 style={{ fontSize: 22 }}>{d.ejercicio.nombre}</h1>
        <p className="muted" style={{ fontSize: 13.5 }}>
          {d.ejercicio.musculo_principal} · {d.ejercicio.maquinas.length ? d.ejercicio.maquinas.join(' o ') : EQUIPO[d.ejercicio.categoria_equipo]}
        </p>
      </header>

      <div className="grid-2">
        <div className="card kpi"><b>🏆 {marca(d.mejor.peso_kg, d.mejor.repeticiones)}</b><span>Tu récord</span></div>
        <div className="card kpi"><b>{conPeso ? kg(d.peso_actual_kg) : `${d.ultima.at(-1)?.repeticiones ?? 0} reps`}</b><span>Última vez · {fechaCorta(d.ultima_fecha)}</span></div>
        <div className="card kpi"><b>{d.veces}</b><span>{d.veces === 1 ? 'Sesión' : 'Sesiones'} desde el {fechaCorta(d.primera_fecha)}</span></div>
        <div className="card kpi"><b>{cambio > 0 ? '▲ ' : cambio < 0 ? '▼ ' : ''}{kg(Math.abs(cambio))}</b><span>Desde la primera vez</span></div>
      </div>

      {d.sugerencia && (
        <section className="card stack" style={{ gap: 6 }}>
          <h2 style={{ fontSize: 15 }}>La próxima vez</h2>
          <PillPeso s={d.sugerencia} />
        </section>
      )}
      {d.estancamiento && <Aviso tipo="info"><b>⏸️ {d.estancamiento.titulo}.</b> {d.estancamiento.texto}</Aviso>}

      {conPeso && d.historial.length > 1 && <GraficoEvolucion puntos={d.historial} />}

      <section className="stack" style={{ gap: 8 }} aria-labelledby="sesiones-ejercicio">
        <h2 id="sesiones-ejercicio" style={{ fontSize: 17 }}>Cada sesión</h2>
        {[...d.historial].reverse().map(v => (
          <Link key={v.sesion_id} to={`/sesion/${v.sesion_id}`} className="card stack" style={{ gap: 4, textDecoration: 'none', color: 'inherit' }}>
            <span className="fila" style={{ justifyContent: 'space-between', gap: 8 }}>
              <b style={{ fontSize: 14.5 }}>{fechaCorta(v.fecha, true)}</b>
              {v.gym_nombre && <span className="muted fila" style={{ fontSize: 12.5, gap: 4 }}><IconMapPin width={13} height={13} /> {v.gym_nombre}</span>}
            </span>
            <span style={{ fontSize: 13.5 }}>
              {v.series.map(s => `${marca(s.peso_kg, s.repeticiones)}${s.es_record ? ' 🏆' : ''}`).join(' · ')}
            </span>
            {v.volumen_kg > 0 && <span className="muted" style={{ fontSize: 12 }}>Volumen: {kg(v.volumen_kg)}</span>}
          </Link>
        ))}
      </section>
    </div>
  );
}

/**
 * Una sola serie (peso más alto de cada sesión) en el tiempo: línea de 2 px, puntos de 8 px, cuadrícula discreta y sin
 * leyenda (el título la nombra). Los récords llevan 🏆 además del color. Al tocar o pasar por un punto se ve su dato;
 * la lista "Cada sesión" de abajo es la vista en tabla.
 */
function GraficoEvolucion({ puntos }: { puntos: VezEjercicio[] }) {
  const [activo, setActivo] = useState<number | null>(null);
  const W = 340, H = 180, izq = 40, der = 14, arr = 16, aba = 26;
  const pesos = puntos.map(p => p.peso_max_kg);
  const min = Math.min(...pesos), max = Math.max(...pesos);
  const paso = Math.max(2.5, Math.ceil((max - min) / 3 / 2.5) * 2.5 || 2.5);
  const y0 = Math.max(0, Math.floor(min / paso) * paso - (max === min ? paso : 0));
  const y1 = Math.ceil(max / paso) * paso + (max === min ? paso : 0);
  const marcas: number[] = [];
  for (let v = y0; v <= y1 + 1e-9; v += paso) marcas.push(v);
  const x = (i: number) => izq + (puntos.length === 1 ? 0 : (i * (W - izq - der)) / (puntos.length - 1));
  const y = (v: number) => arr + (1 - (v - y0) / (y1 - y0 || 1)) * (H - arr - aba);
  const linea = puntos.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.peso_max_kg).toFixed(1)}`).join(' ');
  const sel = activo != null ? puntos[activo] : null;

  return (
    <section className="card stack" style={{ gap: 8 }} aria-labelledby="grafico-titulo">
      <div className="fila" style={{ justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
        <h2 id="grafico-titulo" style={{ fontSize: 15 }}>Peso más alto por sesión</h2>
        <span className="muted" style={{ fontSize: 12.5 }}>🏆 = récord</span>
      </div>
      <p className="grafico-dato" aria-live="polite">
        {sel ? <><b>{fechaCorta(sel.fecha)}:</b> {marca(sel.peso_max_kg, sel.reps_con_peso_max)}{sel.record ? ' · 🏆 récord' : ''}</>
          : <span className="muted">Toca un punto para ver el detalle</span>}
      </p>
      <svg viewBox={`0 0 ${W} ${H}`} className="grafico" role="img"
        aria-label={`Peso más alto en ${puntos.length} sesiones: de ${kg(pesos[0])} a ${kg(pesos.at(-1)!)}`}
        onMouseLeave={() => setActivo(null)}>
        {marcas.map(v => (
          <g key={v}>
            <line x1={izq} x2={W - der} y1={y(v)} y2={y(v)} className="grafico-grilla" />
            <text x={izq - 6} y={y(v) + 4} textAnchor="end" className="grafico-eje">{v.toLocaleString('es')}</text>
          </g>
        ))}
        <text x={izq} y={H - 6} className="grafico-eje">{fechaCorta(puntos[0].fecha)}</text>
        <text x={W - der} y={H - 6} textAnchor="end" className="grafico-eje">{fechaCorta(puntos.at(-1)!.fecha)}</text>
        {sel && <line x1={x(activo!)} x2={x(activo!)} y1={arr} y2={H - aba} className="grafico-guia" />}
        <path d={linea} className="grafico-linea" />
        {puntos.map((p, i) => (
          <g key={p.sesion_id}>
            <circle cx={x(i)} cy={y(p.peso_max_kg)} r={p.record ? 6 : 4.5} className={p.record ? 'grafico-punto record' : 'grafico-punto'} />
            {p.record && <text x={x(i)} y={y(p.peso_max_kg) - 10} textAnchor="middle" fontSize="11" aria-hidden="true">🏆</text>}
            {/* área de toque más grande que el punto */}
            <circle cx={x(i)} cy={y(p.peso_max_kg)} r={14} fill="transparent" style={{ cursor: 'pointer' }}
              onMouseEnter={() => setActivo(i)} onClick={() => setActivo(i)}>
              <title>{`${fechaCorta(p.fecha)}: ${marca(p.peso_max_kg, p.reps_con_peso_max)}${p.record ? ' (récord)' : ''}`}</title>
            </circle>
          </g>
        ))}
      </svg>
    </section>
  );
}
