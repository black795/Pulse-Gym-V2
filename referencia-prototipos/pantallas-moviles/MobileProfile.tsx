import { useNavigate } from 'react-router';
import { useAuth } from '../../features/auth/AuthContext';
import { clients } from '../../data/mock';
import Avatar from '../../components/Avatar';
import { IconCamera, IconAlertTriangle } from '../../components/Icons';

const daniela = clients[0];

export default function MobileProfile() {
  const navigate = useNavigate();
  const { usuario, logout } = useAuth();
  const nombre = usuario?.nombre ?? daniela.name;

  return (
    <div style={{ background: '#fff', minHeight: '100%' }}>
      <div style={{
        background: 'var(--sidebar)', padding: '52px 16px 30px',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
      }}>
        <Avatar name={nombre} photo={usuario?.email === 'daniela@pulsegym.com' ? daniela.photo : null} size={80} />
        <div>
          <div style={{ fontFamily: 'var(--font-sora)', color: '#fff', fontWeight: 800, fontSize: 20, textAlign: 'center' }}>{nombre}</div>
          <div style={{ color: '#8fad99', fontSize: 12.5, textAlign: 'center', marginTop: 2 }}>{usuario?.email}</div>
          <div style={{ color: '#4d7a5e', fontSize: 13, textAlign: 'center', marginTop: 4 }}>Plan {daniela.plan} · {daniela.goal}</div>
        </div>
      </div>

      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {daniela.injury && (
          <div style={{ background: 'var(--danger-tint)', border: '1px solid #fecaca', borderRadius: 12, padding: '12px 14px', display: 'flex', gap: 10 }}>
            <IconAlertTriangle style={{ color: 'var(--danger)', width: 18, height: 18, flexShrink: 0 }} />
            <div>
              <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 700, fontSize: 13.5, color: 'var(--danger)' }}>Lesión activa — {daniela.injury.zone}</div>
              <div style={{ fontSize: 12, color: '#991b1b', marginTop: 2 }}>Rutina ajustada automáticamente</div>
            </div>
          </div>
        )}

        <button onClick={() => navigate('/mobile/camera')} style={{
          display: 'flex', alignItems: 'center', gap: 12,
          background: 'var(--sidebar)', border: '1px solid rgba(182,255,69,0.2)', borderRadius: 12, padding: '14px 16px',
          cursor: 'pointer', width: '100%', textAlign: 'left',
        }}>
          <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'rgba(182,255,69,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <IconCamera style={{ color: 'var(--neon)', width: 20, height: 20 }} />
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 14, color: '#fff' }}>Agregar máquina</div>
            <div style={{ color: '#4d7a5e', fontSize: 12, marginTop: 1 }}>Capturar y clasificar con IA</div>
          </div>
        </button>

        <div style={{ background: 'var(--bg)', borderRadius: 12, border: '1px solid var(--border)' }}>
          {[
            { label: 'Peso actual', value: `${daniela.weight} kg` },
            { label: 'Altura', value: `${daniela.height} cm` },
            { label: 'Objetivo', value: daniela.goal },
            { label: 'Plan', value: daniela.plan },
          ].map((item, i, arr) => (
            <div key={item.label} style={{
              padding: '13px 16px', display: 'flex', justifyContent: 'space-between',
              borderBottom: i < arr.length - 1 ? '1px solid var(--border)' : 'none',
            }}>
              <span style={{ color: 'var(--muted)', fontSize: 13.5 }}>{item.label}</span>
              <span style={{ fontFamily: 'var(--font-sora)', fontWeight: 700, fontSize: 13.5, color: 'var(--ink)' }}>{item.value}</span>
            </div>
          ))}
        </div>

        <button onClick={logout} style={{
          height: 44, background: 'var(--danger-tint)', color: 'var(--danger)', border: '1px solid #fecaca',
          borderRadius: 10, fontFamily: 'var(--font-sora)', fontWeight: 700, fontSize: 14, cursor: 'pointer',
        }}>
          Cerrar sesión
        </button>
      </div>
    </div>
  );
}
