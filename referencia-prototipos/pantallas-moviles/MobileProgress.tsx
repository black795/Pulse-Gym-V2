import { clients } from '../../data/mock';

const daniela = clients[0];

export default function MobileProgress() {
  const measurements = daniela.measurements;
  const max = Math.max(...measurements.map(m => m.weight));

  return (
    <div style={{ background: '#fff', minHeight: '100%' }}>
      <div style={{ background: 'var(--sidebar)', padding: '52px 16px 20px' }}>
        <div style={{ fontFamily: 'var(--font-sora)', color: '#fff', fontWeight: 800, fontSize: 20 }}>Mi progreso</div>
        <div style={{ color: '#4d7a5e', fontSize: 13, marginTop: 4 }}>Historial de mediciones</div>
      </div>

      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {measurements.map((m, i) => (
          <div key={i} style={{ background: i === 0 ? 'var(--primary-tint)' : 'var(--bg)', border: `1px solid ${i === 0 ? '#bbf7d0' : 'var(--border)'}`, borderRadius: 12, padding: '14px 16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 20, color: i === 0 ? 'var(--primary)' : 'var(--ink)' }}>
                {m.weight} kg
              </div>
              <div style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 600 }}>{m.date}</div>
            </div>
            <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>IMC: <strong>{m.bmi.toFixed(1)}</strong></span>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>Cintura: <strong>{m.waist} cm</strong></span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
