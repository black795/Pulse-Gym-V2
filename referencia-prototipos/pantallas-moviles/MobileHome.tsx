import { useNavigate } from 'react-router';
import { useAuth } from '../../features/auth/AuthContext';
import { primerNombre } from '../../features/auth/permisos';
import { clients } from '../../data/mock';
import { IconZap } from '../../components/Icons';
import Avatar from '../../components/Avatar';

const daniela = clients[0];
const days = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
const completed = [0, 1, 2]; // Mon, Tue, Wed done

export default function MobileHome() {
  const navigate = useNavigate();
  const { usuario } = useAuth();

  return (
    <div style={{ background: '#fff', minHeight: '100%' }}>
      {/* Header */}
      <div style={{
        background: 'var(--sidebar)',
        padding: '52px 20px 20px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ color: '#4d7a5e', fontSize: 13, fontWeight: 500 }}>Jueves, 17 sep</div>
          <div style={{ fontFamily: 'var(--font-sora)', color: '#fff', fontSize: 22, fontWeight: 800, marginTop: 2 }}>
            Hola, {primerNombre(usuario)} 👋
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Avatar name={usuario?.nombre ?? daniela.name} photo={usuario?.email === 'daniela@pulsegym.com' ? daniela.photo : null} size={42} />
        </div>
      </div>

      <div style={{ padding: '20px 16px' }}>
        {/* Today's workout card */}
        <div style={{
          borderRadius: 16, overflow: 'hidden', marginBottom: 20,
          boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
        }}>
          <div style={{
            backgroundImage: 'url(https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800&h=400&fit=crop&auto=format)',
            backgroundSize: 'cover', backgroundPosition: 'center',
            height: 160, position: 'relative',
          }}>
            <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to bottom, transparent 30%, rgba(10,18,13,0.85))' }} />
            <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '14px 16px' }}>
              <div style={{ color: 'var(--neon)', fontSize: 11, fontWeight: 800, letterSpacing: '0.08em' }}>HOY · VIERNES</div>
              <div style={{ fontFamily: 'var(--font-sora)', color: '#fff', fontSize: 17, fontWeight: 800, marginTop: 2 }}>
                Piernas + Core
              </div>
            </div>
          </div>
          <div style={{ background: 'var(--sidebar)', padding: '14px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontSize: 13, color: '#8fad99' }}>4 ejercicios · ~50 min</div>
            <button onClick={() => navigate('/mobile/workout')} style={{
              background: 'var(--neon)', color: 'var(--sidebar)', border: 'none',
              borderRadius: 8, padding: '8px 18px', fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 13, cursor: 'pointer',
            }}>
              Comenzar
            </button>
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 20 }}>
          {[
            { label: 'Peso', value: '58 kg', sub: '-1 kg' },
            { label: 'Racha', value: '5 días', sub: '🔥' },
            { label: 'Este mes', value: '12 ses.', sub: '+2' },
          ].map(s => (
            <div key={s.label} style={{
              background: 'var(--bg)', borderRadius: 12, padding: '14px 12px',
              border: '1px solid var(--border)', textAlign: 'center',
            }}>
              <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 17, color: 'var(--ink)' }}>{s.value}</div>
              <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 2 }}>{s.label}</div>
              <div style={{ fontSize: 11, color: 'var(--primary)', fontWeight: 700, marginTop: 2 }}>{s.sub}</div>
            </div>
          ))}
        </div>

        {/* AI trainer card */}
        <div onClick={() => navigate('/mobile/ai')} style={{
          background: 'var(--sidebar)', borderRadius: 14, padding: '16px 18px',
          marginBottom: 20, cursor: 'pointer',
          border: '1px solid rgba(182,255,69,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 40, height: 40, borderRadius: '50%', background: 'var(--neon)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <IconZap style={{ color: 'var(--sidebar)', width: 20, height: 20 }} />
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-sora)', color: '#fff', fontWeight: 800, fontSize: 14 }}>Entrenador IA</div>
              <div style={{ color: '#4d7a5e', fontSize: 12, marginTop: 1 }}>Ajusté tu rutina — rodilla detectada</div>
            </div>
          </div>
          <div style={{ color: 'var(--neon)', fontSize: 20 }}>›</div>
        </div>

        {/* Week progress */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: '16px 18px' }}>
          <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 14, marginBottom: 14, color: 'var(--ink)' }}>Esta semana</div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'space-between' }}>
            {days.map((d, i) => (
              <div key={d} style={{
                flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
              }}>
                <div style={{
                  width: 36, height: 36, borderRadius: '50%',
                  background: completed.includes(i) ? 'var(--primary)' : i === 3 ? 'var(--primary-tint)' : 'var(--bg)',
                  border: `1.5px solid ${completed.includes(i) ? 'var(--primary)' : i === 3 ? 'var(--primary)' : 'var(--border)'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 12, fontWeight: 800,
                  color: completed.includes(i) ? '#fff' : i === 3 ? 'var(--primary)' : 'var(--muted-2)',
                }}>
                  {completed.includes(i) ? '✓' : d}
                </div>
                <div style={{ fontSize: 10, color: 'var(--muted-2)', fontWeight: 700 }}>{d}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
