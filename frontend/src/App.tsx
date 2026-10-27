import { BrowserRouter, Route, Routes } from 'react-router';
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

/** Las pantallas sin barra inferior también se ven como celular centrado en el computador. */
function Frame({ children }: { children: React.ReactNode }) {
  return <div className="app-frame">{children}</div>;
}
