import { Link, NavLink, Outlet, useNavigate } from 'react-router';
import Avatar from '../components/Avatar';
import { IconBandage, IconCalendar, IconDumbbell, IconHome, IconLogOut, IconSearch, IconUser } from '../components/Icons';
import { Logo } from '../components/UI';
import { useAuth } from '../features/auth/AuthContext';

const ITEMS = [
  { a: '/', t: 'Hoy', i: IconHome, fin: true },
  { a: '/plan', t: 'Plan', i: IconCalendar },
  { a: '/gyms', t: 'Mis gyms', i: IconDumbbell },
  { a: '/lesiones', t: 'Lesiones', i: IconBandage },
  { a: '/perfil', t: 'Perfil', i: IconUser },
];

/**
 * Marco de la app. En el celular: contenido arriba y barra de pestañas abajo.
 * Desde 768px: sidebar fijo a la izquierda y el contenido centrado (la barra inferior se oculta por CSS).
 */
export default function AppShell() {
  return (
    <div className="app-frame app-shell">
      <Sidebar />
      <main className="app-main"><div className="app-contenido"><Outlet /></div></main>
      <nav className="nav-inferior" aria-label="Principal">
        {ITEMS.map(({ a, t, i: Icono, fin }) => (
          <NavLink key={a} to={a} end={fin}><Icono width={22} height={22} />{t}</NavLink>
        ))}
      </nav>
    </div>
  );
}

function Sidebar() {
  const nav = useNavigate();
  const { usuario, logout } = useAuth();
  return (
    <aside className="sidebar">
      <Link to="/" style={{ color: 'inherit', textDecoration: 'none', padding: '0 8px' }} aria-label="Pulse Gym, ir a Hoy"><Logo tamano={38} /></Link>
      <nav aria-label="Principal (escritorio)">
        {ITEMS.map(({ a, t, i: Icono, fin }) => (
          <NavLink key={a} to={a} end={fin}><Icono width={20} height={20} />{t}</NavLink>
        ))}
        <span className="sidebar-titulo">Explorar</span>
        <NavLink to="/ejercicios"><IconSearch width={20} height={20} />Catálogo de ejercicios</NavLink>
      </nav>
      {usuario && (
        <div className="sidebar-usuario">
          <div className="fila" style={{ minWidth: 0 }}>
            <Avatar name={usuario.nombre} size={40} />
            <div style={{ minWidth: 0 }}>
              <b style={{ display: 'block', fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{usuario.nombre}</b>
              <span className="muted" style={{ display: 'block', fontSize: 12.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{usuario.email}</span>
            </div>
          </div>
          <div className="sidebar-acciones">
            <Link to="/perfil"><IconUser width={15} height={15} /> Mi perfil</Link>
            <button type="button" onClick={() => { logout(); nav('/login', { replace: true }); }}><IconLogOut width={15} height={15} /> Salir</button>
          </div>
        </div>
      )}
    </aside>
  );
}
