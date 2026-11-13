/**
 * Sprint 5 (PG-41/PG-42): el peso sugerido de un ejercicio. La primera vez es una estimación (de la IA, acotada por
 * reglas, o solo de reglas); después sale de tu historial (subir, mantener, bajar o volver tras una ausencia).
 */
import type { PesoSugerido } from '../lib/tipos';

const ICONO: Record<PesoSugerido['tipo'], string> = { inicial: '✨', subir: '📈', mantener: '🎯', bajar: '↘️', retorno: '🔄' };
const CLASE: Record<PesoSugerido['tipo'], string> = {
  inicial: 'peso-inicial', subir: 'peso-subir', mantener: 'peso-mantener', bajar: 'peso-bajar', retorno: 'peso-bajar',
};

export const kg = (n: number) => `${n.toLocaleString('es', { maximumFractionDigits: 1 })} kg`;

/** Pastilla con la explicación completa (sesión en vivo). */
export function PillPeso({ s }: { s: PesoSugerido | null | undefined }) {
  if (!s) return null;
  return <p className={`pill-peso ${CLASE[s.tipo]}`}><span aria-hidden="true">{ICONO[s.tipo]}</span> {s.texto}</p>;
}

/** Línea corta para listas (plan, hoy): "Peso sugerido: 42,5 kg · sube". */
export function LineaPeso({ s }: { s: PesoSugerido | null | undefined }) {
  if (!s) return null;
  const detalle = {
    inicial: s.origen === 'ia' ? 'primera vez, estimado por la IA' : 'primera vez, estimado según tu perfil',
    subir: 'sube respecto a la vez pasada', mantener: 'igual que la vez pasada', bajar: 'baja un poco', retorno: 'más suave porque volviste',
  }[s.tipo];
  return (
    <span className={`linea-peso ${CLASE[s.tipo]}`} title={s.texto}>
      <span aria-hidden="true">{ICONO[s.tipo]}</span> {s.peso_kg > 0 ? <>Peso sugerido: <b>{kg(s.peso_kg)}</b></> : <>Meta: <b>{s.reps} reps</b></>} · {detalle}
    </span>
  );
}
