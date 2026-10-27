/** Porteros de las rutas: sin sesión → login; con sesión, el login no tiene sentido → inicio. */
import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';
import PantallaCarga from '../../pages/PantallaCarga';
import { useAuth } from './AuthContext';

export function RequiereSesion({ children }: { children: ReactNode }) {
  const { usuario, cargando } = useAuth();
  const location = useLocation();
  if (cargando) return <PantallaCarga />;
  if (!usuario) return <Navigate to="/login" replace state={{ desde: location.pathname + location.search }} />;
  return <>{children}</>;
}

export function SoloInvitados({ children }: { children: ReactNode }) {
  const { usuario, cargando } = useAuth();
  if (cargando) return <PantallaCarga />;
  if (usuario) return <Navigate to="/" replace />;
  return <>{children}</>;
}
