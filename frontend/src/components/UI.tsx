import { useId, type InputHTMLAttributes, type ReactNode } from 'react';
import { Link } from 'react-router';
import { IconArrowLeft, IconPulse } from './Icons';

export function Campo({ etiqueta, ayuda, error, ...props }: { etiqueta: string; ayuda?: string; error?: string | null } & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <div className="campo">
      <label htmlFor={id}>{etiqueta}</label>
      <input id={id} className="input" aria-invalid={!!error} aria-describedby={`${id}-a`} {...props} />
      {(error || ayuda) && <div id={`${id}-a`} className="ayuda" style={error ? { color: 'var(--danger)' } : undefined}>{error ?? ayuda}</div>}
    </div>
  );
}

export function Aviso({ tipo = 'error', children }: { tipo?: 'error' | 'ok' | 'info'; children: ReactNode }) {
  return <div className={`aviso aviso-${tipo}`} role={tipo === 'error' ? 'alert' : 'status'}>{children}</div>;
}

export function Logo({ tamano = 44 }: { tamano?: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{ width: tamano, height: tamano, borderRadius: tamano / 3.2, background: 'var(--neon)', display: 'grid', placeItems: 'center' }}>
        <IconPulse style={{ color: 'var(--sidebar)', width: tamano * .55, height: tamano * .55, strokeWidth: 2.5 }} />
      </div>
      <span style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: tamano * .5 }}>Pulse Gym</span>
    </div>
  );
}

export function Volver({ a, texto = 'Volver' }: { a: string; texto?: string }) {
  return (
    <Link to={a} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'inherit', textDecoration: 'none', fontWeight: 700, fontSize: 14, minHeight: 44 }}>
      <IconArrowLeft width={18} height={18} /> {texto}
    </Link>
  );
}

export function Insignia({ tono, children }: { tono: 'ok' | 'aviso' | 'peligro' | 'neutro'; children: ReactNode }) {
  const t = {
    ok: ['var(--primary-tint)', 'var(--primary-dark)'], aviso: ['var(--warning-tint)', 'var(--warning)'],
    peligro: ['var(--danger-tint)', 'var(--danger)'], neutro: ['#EEF2EF', 'var(--muted)'],
  }[tono];
  return <span className="insignia" style={{ background: t[0], color: t[1] }}>{children}</span>;
}

/** Botones de elección única (objetivo, nivel, sexo…). */
export function Opciones<T extends string | number>({ valor, onCambio, opciones, columnas = 1 }: {
  valor: T | null | undefined; onCambio: (v: T) => void; opciones: { valor: T; texto: string }[]; columnas?: number;
}) {
  return (
    <div className="opciones" style={{ gridTemplateColumns: `repeat(${columnas}, 1fr)` }}>
      {opciones.map(o => (
        <button type="button" key={String(o.valor)} className="opcion" aria-pressed={valor === o.valor} onClick={() => onCambio(o.valor)}>{o.texto}</button>
      ))}
    </div>
  );
}

/** Convierte "72,5" o "72.5" en número; vacío → undefined. */
export function aNumero(t: string): number | undefined {
  const n = Number(t.trim().replace(',', '.'));
  return t.trim() === '' || Number.isNaN(n) ? undefined : n;
}
