import { Outlet, NavLink } from 'react-router';
import { IconHome, IconList, IconZap, IconActivity, IconUser } from '../../components/Icons';

const navItems = [
  { to: '/mobile', icon: IconHome, label: 'Inicio' },
  { to: '/mobile/workout', icon: IconList, label: 'Rutina' },
  { to: '/mobile/ai', icon: IconZap, label: 'IA' },
  { to: '/mobile/progress', icon: IconActivity, label: 'Progreso' },
  { to: '/mobile/profile', icon: IconUser, label: 'Perfil' },
];

export default function MobileShell() {
  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
    }}>
      {/* Mobile frame */}
      <div style={{
        width: '100%', maxWidth: 430,
        minHeight: '100vh', background: '#fff',
        display: 'flex', flexDirection: 'column',
        position: 'relative', boxShadow: '0 0 40px rgba(0,0,0,0.12)',
      }}>
        <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 80 }}>
          <Outlet />
        </div>

        {/* Bottom nav */}
        <div style={{
          position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)',
          width: '100%', maxWidth: 430,
          background: '#fff', borderTop: '1px solid var(--border)',
          display: 'flex', padding: '8px 0 12px',
          zIndex: 100,
        }}>
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/mobile'}
              style={({ isActive }) => ({
                flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
                textDecoration: 'none', padding: '4px 0',
                color: isActive ? 'var(--primary)' : 'var(--muted-2)',
              })}
            >
              {({ isActive }) => (
                <>
                  <item.icon style={{ width: 22, height: 22 }} />
                  <span style={{ fontSize: 10.5, fontWeight: 700, fontFamily: 'var(--font-sora)' }}>{item.label}</span>
                  {isActive && (
                    <div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--primary)' }} />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </div>
    </div>
  );
}
