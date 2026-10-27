import { useState } from 'react';
import { useNavigate } from 'react-router';
import { clients, planBOptions } from '../../data/mock';
import { IconX, IconCheck } from '../../components/Icons';

const daniela = clients[0];
const workoutExercises = daniela.routine!.schedule['Viernes'];

function SetRow({ series, prev, kgInit, reps }: { series: number; prev: string; kgInit: string; reps: string }) {
  const [kg, setKg] = useState(kgInit);
  const [r, setR] = useState(reps);
  const [done, setDone] = useState(false);
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '36px 1fr 1fr 1fr 36px',
      alignItems: 'center', gap: 8, padding: '8px 0',
      borderBottom: '1px solid var(--border)', opacity: done ? 0.5 : 1,
    }}>
      <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 700, fontSize: 14, color: 'var(--ink)', textAlign: 'center' }}>{series}</div>
      <div style={{ fontSize: 12, color: 'var(--muted)', textAlign: 'center' }}>{prev}</div>
      <input value={kg} onChange={e => setKg(e.target.value)} style={{
        height: 36, textAlign: 'center', border: '1.5px solid var(--border)', borderRadius: 8,
        fontFamily: 'var(--font-sora)', fontWeight: 700, fontSize: 14, outline: 'none',
        background: 'var(--bg)', width: '100%',
      }} />
      <input value={r} onChange={e => setR(e.target.value)} style={{
        height: 36, textAlign: 'center', border: '1.5px solid var(--border)', borderRadius: 8,
        fontFamily: 'var(--font-sora)', fontWeight: 700, fontSize: 14, outline: 'none',
        background: 'var(--bg)', width: '100%',
      }} />
      <button onClick={() => setDone(!done)} style={{
        width: 32, height: 32, borderRadius: '50%', cursor: 'pointer',
        background: done ? 'var(--primary)' : 'var(--bg)',
        border: `1.5px solid ${done ? 'var(--primary)' : 'var(--border)'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        {done && <IconCheck style={{ color: '#fff', width: 14, height: 14 }} />}
      </button>
    </div>
  );
}

export default function MobileWorkout() {
  const navigate = useNavigate();
  const [elapsed, setElapsed] = useState('32:14');
  const [selectedPlanB, setSelectedPlanB] = useState(0);

  return (
    <div style={{ background: '#fff', minHeight: '100%' }}>
      {/* Header */}
      <div style={{
        background: 'var(--sidebar)', padding: '52px 16px 16px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ fontFamily: 'var(--font-sora)', color: '#fff', fontWeight: 800, fontSize: 17 }}>Entrenamiento activo</div>
        <button onClick={() => navigate('/mobile')} style={{
          background: 'var(--danger)', color: '#fff', border: 'none', borderRadius: 8,
          padding: '6px 14px', fontFamily: 'var(--font-sora)', fontWeight: 700, fontSize: 12, cursor: 'pointer',
        }}>
          Finalizar
        </button>
      </div>

      {/* Stats strip */}
      <div style={{ background: 'var(--black-2)', display: 'flex', padding: '12px 16px', gap: 0 }}>
        {[
          { label: 'Duración', value: elapsed },
          { label: 'Volumen', value: '2,240 kg' },
          { label: 'Series', value: '6/12' },
        ].map((s, i) => (
          <div key={s.label} style={{
            flex: 1, textAlign: 'center',
            borderRight: i < 2 ? '1px solid rgba(255,255,255,0.1)' : 'none',
          }}>
            <div style={{ fontFamily: 'var(--font-sora)', color: 'var(--neon)', fontWeight: 800, fontSize: 16 }}>{s.value}</div>
            <div style={{ color: '#4d7a5e', fontSize: 11, fontWeight: 600 }}>{s.label}</div>
          </div>
        ))}
      </div>

      <div style={{ padding: '16px' }}>
        {/* Exercise 1 */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: '16px', marginBottom: 14, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <div>
              <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 15, color: 'var(--ink)' }}>Plancha abdominal</div>
              <div style={{ fontSize: 12, color: 'var(--primary)', fontWeight: 700, marginTop: 4, background: 'var(--primary-tint)', display: 'inline-block', padding: '2px 10px', borderRadius: 999 }}>
                📈 68 kg · +8 kg en 4 semanas
              </div>
            </div>
            <span style={{ fontSize: 11, color: 'var(--primary)', fontWeight: 700 }}>● Disponible</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '36px 1fr 1fr 1fr 36px', gap: 8, marginBottom: 4 }}>
            {['#', 'Ant.', 'Kg', 'Reps', ''].map(h => (
              <div key={h} style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--muted)', textAlign: 'center' }}>{h}</div>
            ))}
          </div>
          <SetRow series={1} prev="--" kgInit="--" reps="45" />
          <SetRow series={2} prev="--" kgInit="--" reps="45" />
          <SetRow series={3} prev="--" kgInit="--" reps="45" />
        </div>

        {/* Exercise 2 — occupied machine */}
        <div style={{ background: 'var(--surface)', border: '1.5px solid #fecaca', borderRadius: 14, padding: '16px', marginBottom: 14, boxShadow: '0 1px 4px rgba(220,38,38,0.08)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 15, color: 'var(--ink)' }}>Peso muerto rumano</div>
            <span style={{ fontSize: 11, color: 'var(--danger)', fontWeight: 800, background: 'var(--danger-tint)', padding: '2px 8px', borderRadius: 999 }}>● Máquina ocupada</span>
          </div>

          <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 12, background: 'var(--neon)', color: 'var(--sidebar)', padding: '3px 10px', borderRadius: 6, display: 'inline-block', marginBottom: 10 }}>
            IA — Plan B
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {planBOptions.map((opt, i) => (
              <div key={opt.id} onClick={() => setSelectedPlanB(i)} style={{
                padding: '10px 14px', borderRadius: 10, cursor: 'pointer',
                background: selectedPlanB === i ? 'var(--primary-tint)' : 'var(--bg)',
                border: `1.5px solid ${selectedPlanB === i ? 'var(--primary)' : 'var(--border)'}`,
                display: 'flex', gap: 10, alignItems: 'center',
              }}>
                <div style={{
                  width: 18, height: 18, borderRadius: '50%', flexShrink: 0,
                  background: selectedPlanB === i ? 'var(--primary)' : 'transparent',
                  border: `2px solid ${selectedPlanB === i ? 'var(--primary)' : 'var(--border)'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {selectedPlanB === i && <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff' }} />}
                </div>
                <div>
                  <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 700, fontSize: 13, color: 'var(--ink)' }}>{opt.label}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 2 }}>{opt.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Exercise 3 — partially visible */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: '16px', opacity: 0.5, maxHeight: 80, overflow: 'hidden' }}>
          <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 15, color: 'var(--ink)' }}>Hip thrust</div>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>3 series · 12 reps · 60 kg</div>
        </div>
        <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--muted-2)', marginTop: 6 }}>↓ Desplazar para ver más</div>
      </div>
    </div>
  );
}
