import { useState } from 'react';
import { useNavigate } from 'react-router';

const groups = ['Piernas', 'Pecho', 'Espalda', 'Hombros', 'Brazos', 'Cardio'];

export default function MobileConfirm() {
  const navigate = useNavigate();
  const [name, setName] = useState('Prensa de piernas');
  const [group, setGroup] = useState('Piernas');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => navigate('/mobile'), 1500);
  };

  if (saved) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: 16, background: '#fff', padding: 24 }}>
        <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'var(--primary-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28 }}>✓</div>
        <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 20, color: 'var(--ink)', textAlign: 'center' }}>Máquina guardada</div>
        <div style={{ color: 'var(--muted)', fontSize: 14 }}>Redirigiendo al inicio...</div>
      </div>
    );
  }

  return (
    <div style={{ background: '#fff', minHeight: '100%' }}>
      {/* Photo */}
      <div style={{ position: 'relative', height: 280 }}>
        <img
          src="https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=430&h=280&fit=crop&auto=format"
          alt="Máquina capturada"
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        />
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to bottom, transparent 50%, rgba(10,18,13,0.7))' }} />
        <div style={{ position: 'absolute', bottom: 16, left: 16 }}>
          <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: 12, marginBottom: 4 }}>Fotografía tomada</div>
        </div>
      </div>

      {/* AI result */}
      <div style={{ margin: '16px', background: 'var(--sidebar)', borderRadius: 14, padding: '16px 18px', border: '1px solid rgba(182,255,69,0.2)' }}>
        <div style={{ color: 'var(--neon)', fontSize: 11, fontWeight: 800, letterSpacing: '0.08em', marginBottom: 10 }}>CLASIFICACIÓN IA</div>
        <div style={{ fontFamily: 'var(--font-sora)', color: '#fff', fontWeight: 800, fontSize: 22, marginBottom: 6 }}>Prensa de piernas</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ background: 'rgba(182,255,69,0.12)', border: '1px solid rgba(182,255,69,0.3)', borderRadius: 8, padding: '6px 14px' }}>
            <div style={{ color: 'var(--neon)', fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 18 }}>92%</div>
            <div style={{ color: '#4d7a5e', fontSize: 11, fontWeight: 600 }}>Confianza</div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.07)', borderRadius: 8, padding: '6px 14px' }}>
            <div style={{ color: '#8fad99', fontWeight: 700, fontSize: 14 }}>Piernas</div>
            <div style={{ color: '#4d7a5e', fontSize: 11, fontWeight: 600 }}>Grupo muscular</div>
          </div>
        </div>
      </div>

      {/* Editable fields */}
      <div style={{ padding: '0 16px 16px' }}>
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: '16px' }}>
          <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 14, marginBottom: 14, color: 'var(--ink)' }}>Confirmar o editar</div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, marginBottom: 5, color: 'var(--muted)' }}>Nombre de la máquina</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              style={{
                width: '100%', height: 44, padding: '0 12px',
                border: '1.5px solid var(--border)', borderRadius: 8,
                fontFamily: 'var(--font-manrope)', fontSize: 14, outline: 'none',
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, marginBottom: 8, color: 'var(--muted)' }}>Grupo muscular</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {groups.map(g => (
                <button key={g} onClick={() => setGroup(g)} style={{
                  padding: '6px 14px', borderRadius: 999, cursor: 'pointer',
                  fontFamily: 'var(--font-manrope)', fontWeight: 600, fontSize: 12.5,
                  background: group === g ? 'var(--primary)' : 'var(--bg)',
                  color: group === g ? '#fff' : 'var(--muted)',
                  border: group === g ? 'none' : '1px solid var(--border)',
                }}>
                  {g}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 16 }}>
          <button onClick={handleSave} style={{
            height: 50, background: 'var(--primary)', color: '#fff', border: 'none',
            borderRadius: 10, fontFamily: 'var(--font-sora)', fontWeight: 700, fontSize: 14, cursor: 'pointer',
          }}>
            Guardar y agregar otra
          </button>
          <button onClick={handleSave} style={{
            height: 46, background: 'var(--surface)', color: 'var(--ink)',
            border: '1.5px solid var(--border)', borderRadius: 10,
            fontFamily: 'var(--font-sora)', fontWeight: 700, fontSize: 14, cursor: 'pointer',
          }}>
            Guardar y terminar
          </button>
        </div>
      </div>
    </div>
  );
}
