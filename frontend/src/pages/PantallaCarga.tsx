import { IconPulse } from '../components/Icons';

export default function PantallaCarga() {
  return (
    <div style={{ minHeight: '100dvh', display: 'grid', placeItems: 'center', background: 'var(--sidebar)' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }} role="status" aria-live="polite">
        <div className="pulse-latido" style={{ width: 52, height: 52, borderRadius: 14, background: 'var(--neon)', display: 'grid', placeItems: 'center' }}>
          <IconPulse style={{ color: 'var(--sidebar)', width: 28, height: 28, strokeWidth: 2.5 }} />
        </div>
        <span style={{ color: '#8fad99', fontSize: 13.5, fontWeight: 600 }}>Cargando Pulse Gym…</span>
      </div>
    </div>
  );
}
