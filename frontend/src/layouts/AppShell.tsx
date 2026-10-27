import { NavLink, Outlet } from 'react-router';
import { IconBandage, IconCalendar, IconDumbbell, IconHome, IconUser } from '../components/Icons';

const ITEMS = [
  { a: '/', t: 'Hoy', i: IconHome, fin: true },
  { a: '/plan', t: 'Plan', i: IconCalendar },
  { a: '/gyms', t: 'Mis gyms', i: IconDumbbell },
  { a: '/lesiones', t: 'Lesiones', i: IconBandage },
  { a: '/perfil', t: 'Perfil', i: IconUser },
];

/** Marco de la app en el celular: contenido arriba y barra de pestañas abajo. */
export default function AppShell() {
  return (
    <div className="app-frame">
      <main><Outlet /></main>
      <nav className="nav-inferior" aria-label="Principal">
        {ITEMS.map(({ a, t, i: Icono, fin }) => (
          <NavLink key={a} to={a} end={fin}><Icono width={22} height={22} />{t}</NavLink>
        ))}
      </nav>
    </div>
  );
}
