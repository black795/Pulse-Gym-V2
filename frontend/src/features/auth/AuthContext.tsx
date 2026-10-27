import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { authApi } from '../../lib/endpoints';
import { configurarHttp } from '../../lib/http';
import type { Usuario } from '../../lib/tipos';
import { tokenStorage } from './tokenStorage';

interface AuthValor {
  usuario: Usuario | null;
  cargando: boolean; // true mientras se revisa si ya había una sesión guardada
  login: (email: string, password: string) => Promise<Usuario>;
  registro: (d: { nombre: string; email: string; password: string }) => Promise<Usuario>;
  logout: () => void;
  refrescar: () => Promise<void>; // vuelve a pedir quién soy (ej. tras aceptar el consentimiento)
}

const AuthContext = createContext<AuthValor | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  const logout = useCallback(() => { tokenStorage.borrar(); setUsuario(null); }, []);

  useEffect(() => { configurarHttp({ obtenerToken: tokenStorage.leer, alPerderSesion: logout }); }, [logout]);

  useEffect(() => {
    let activo = true;
    if (!tokenStorage.leer()) { setCargando(false); return; }
    authApi.yo()
      .then(u => activo && setUsuario(u))
      .catch(e => { if (activo && e?.status === 401) logout(); }) // sin internet NO cierra la sesión
      .finally(() => activo && setCargando(false));
    return () => { activo = false; };
  }, [logout]);

  const entrar = (s: { access_token: string; usuario: Usuario }) => { tokenStorage.guardar(s.access_token); setUsuario(s.usuario); return s.usuario; };

  const valor = useMemo<AuthValor>(() => ({
    usuario, cargando, logout,
    login: async (email, password) => entrar(await authApi.login(email, password)),
    registro: async d => entrar(await authApi.registro(d)),
    refrescar: async () => { setUsuario(await authApi.yo()); },
  }), [usuario, cargando, logout]);

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValor {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>');
  return ctx;
}
