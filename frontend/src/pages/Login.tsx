import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { Aviso, Campo, Logo } from '../components/UI';
import { useAuth } from '../features/auth/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const desde = (useLocation().state as { desde?: string } | null)?.desde ?? '/';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError(null); setEnviando(true);
    try { await login(email.trim(), password); nav(desde, { replace: true }); }
    catch (err) { setError(err instanceof Error ? err.message : 'No se pudo iniciar sesión.'); }
    finally { setEnviando(false); }
  }

  return (
    <div className="oscura pantalla-sin-nav">
      <div style={{ padding: '28px 0 32px' }}><Logo /></div>
      <h1 style={{ fontSize: 26, marginBottom: 6 }}>Bienvenido de vuelta</h1>
      <p className="muted" style={{ marginBottom: 24 }}>Entra para ver tu plan de hoy.</p>
      <form className="stack" onSubmit={enviar} noValidate>
        {error && <Aviso>{error}</Aviso>}
        <Campo etiqueta="Correo" type="email" autoComplete="email" inputMode="email" value={email} onChange={e => setEmail(e.target.value)} required />
        <Campo etiqueta="Contraseña" type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required />
        <button className="btn btn-neon" disabled={enviando || !email || !password}>{enviando ? 'Entrando…' : 'Entrar'}</button>
        <Link to="/recuperar" className="btn btn-texto" style={{ alignSelf: 'center' }}>Olvidé mi contraseña</Link>
      </form>
      <p className="muted" style={{ textAlign: 'center', marginTop: 20, fontSize: 14 }}>
        ¿Primera vez? <Link to="/registro" style={{ color: 'var(--neon)', fontWeight: 700 }}>Crear mi cuenta</Link>
      </p>
    </div>
  );
}
