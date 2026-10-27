import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { Aviso, Campo, Logo } from '../components/UI';
import { useAuth } from '../features/auth/AuthContext';

export default function Registro() {
  const { registro } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ nombre: '', email: '', password: '' });
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const cambiar = (k: keyof typeof f) => (e: { target: { value: string } }) => setF(p => ({ ...p, [k]: e.target.value }));

  const pwOk = f.password.length >= 8 && /[A-Za-z]/.test(f.password) && /\d/.test(f.password);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError(null); setEnviando(true);
    try { await registro({ nombre: f.nombre.trim(), email: f.email.trim(), password: f.password }); nav('/', { replace: true }); }
    catch (err) { setError(err instanceof Error ? err.message : 'No se pudo crear la cuenta.'); }
    finally { setEnviando(false); }
  }

  return (
    <div className="oscura pantalla-sin-nav">
      <div style={{ padding: '28px 0 28px' }}><Logo /></div>
      <h1 style={{ fontSize: 26, marginBottom: 6 }}>Crea tu cuenta</h1>
      <p className="muted" style={{ marginBottom: 24 }}>Toma menos de un minuto.</p>
      <form className="stack" onSubmit={enviar} noValidate>
        {error && <Aviso>{error}</Aviso>}
        <Campo etiqueta="Tu nombre" autoComplete="name" value={f.nombre} onChange={cambiar('nombre')} required />
        <Campo etiqueta="Correo" type="email" autoComplete="email" inputMode="email" value={f.email} onChange={cambiar('email')} required />
        <Campo etiqueta="Contraseña" type="password" autoComplete="new-password" value={f.password} onChange={cambiar('password')}
          ayuda={pwOk || !f.password ? 'Mínimo 8 caracteres, con al menos una letra y un número.' : undefined}
          error={f.password && !pwOk ? 'Mínimo 8 caracteres, con al menos una letra y un número.' : null} required />
        <button className="btn btn-neon" disabled={enviando || f.nombre.trim().length < 2 || !f.email || !pwOk}>{enviando ? 'Creando…' : 'Crear cuenta'}</button>
      </form>
      <p className="muted" style={{ textAlign: 'center', marginTop: 20, fontSize: 14 }}>
        ¿Ya tienes cuenta? <Link to="/login" style={{ color: 'var(--neon)', fontWeight: 700 }}>Entrar</Link>
      </p>
    </div>
  );
}
