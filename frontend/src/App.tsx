import { BrowserRouter, Route, Routes } from 'react-router';
import { IconCamera, IconDumbbell, IconShield } from './components/Icons';
import { Logo } from './components/UI';
import { AuthProvider } from './features/auth/AuthContext';
import { RequiereSesion, SoloInvitados } from './features/auth/guards';
import AppShell from './layouts/AppShell';
import AgregarMaquinas from './pages/AgregarMaquinas';
import CatalogoEjercicios from './pages/CatalogoEjercicios';
import Consentimiento from './pages/Consentimiento';
import GymDetalle from './pages/GymDetalle';
import Inicio from './pages/Inicio';
import Lesiones from './pages/Lesiones';
import Login from './pages/Login';
import MisGyms from './pages/MisGyms';
import NoEncontrada from './pages/NoEncontrada';
import Onboarding from './pages/Onboarding';
import Perfil from './pages/Perfil';
import Plan from './pages/Plan';
import Recuperar from './pages/Recuperar';
import Registro from './pages/Registro';
import Restablecer from './pages/Restablecer';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
          <Routes>
            <Route path="/login" element={<SoloInvitados><Frame><Login /></Frame></SoloInvitados>} />
            <Route path="/registro" element={<SoloInvitados><Frame><Registro /></Frame></SoloInvitados>} />
            <Route path="/recuperar" element={<Frame><Recuperar /></Frame>} />
            <Route path="/restablecer" element={<Frame><Restablecer /></Frame>} />
            <Route path="/consentimiento" element={<RequiereSesion><Frame><Consentimiento /></Frame></RequiereSesion>} />
            <Route path="/onboarding" element={<RequiereSesion><Frame><Onboarding /></Frame></RequiereSesion>} />
            <Route element={<RequiereSesion><AppShell /></RequiereSesion>}>
              <Route index element={<Inicio />} />
              <Route path="/plan" element={<Plan />} />
              <Route path="/ejercicios" element={<CatalogoEjercicios />} />
              <Route path="/gyms" element={<MisGyms />} />
              <Route path="/gyms/:id" element={<GymDetalle />} />
              <Route path="/gyms/:id/agregar" element={<AgregarMaquinas />} />
              <Route path="/lesiones" element={<Lesiones />} />
              <Route path="/perfil" element={<Perfil />} />
            </Route>
            <Route path="*" element={<Frame><NoEncontrada /></Frame>} />
          </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

const PUNTOS = [
  { i: IconShield, t: 'Se adapta a tus lesiones', d: 'Si algo te duele, evitamos lo que lo empeora y buscamos reemplazos seguros.' },
  { i: IconCamera, t: 'Reconoce las máquinas con IA', d: 'Toma una foto y la IA identifica la máquina para armar tu inventario.' },
  { i: IconDumbbell, t: 'Rutina hecha para tu gimnasio', d: 'Cada sesión usa solo las máquinas que realmente tiene el lugar donde entrenas.' },
];

/**
 * Pantallas sin barra inferior (entrar, registro, onboarding…). En el celular se ven igual que siempre;
 * desde 900px se muestran en pantalla dividida con el panel de marca a la izquierda.
 */
function Frame({ children }: { children: React.ReactNode }) {
  return (
    <div className="auth-split">
      <aside className="auth-marca" aria-hidden="true">
        <Logo tamano={42} />
        <div className="stack" style={{ gap: 16 }}>
          <h2>Tu entrenador con IA, <em>hecho a tu medida.</em></h2>
          <p className="muted" style={{ fontSize: 15.5, maxWidth: 440 }}>Un plan semanal que entiende tu objetivo, tu cuerpo y el gym donde entrenas.</p>
        </div>
        <ul>
          {PUNTOS.map(({ i: Icono, t, d }) => (
            <li key={t}><span><Icono width={20} height={20} /></span><span><b>{t}</b><p>{d}</p></span></li>
          ))}
        </ul>
      </aside>
      <div className="auth-panel"><div className="app-frame auth-contenido">{children}</div></div>
    </div>
  );
}
