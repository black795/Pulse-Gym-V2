import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Aviso, Campo } from '../components/UI';
import { authApi } from '../lib/endpoints';

export default function Restablecer() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const pwOk = password.length >= 8 && /[A-Za-z]/.test(password) && /\d/.test(password);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError(null); setEnviando(true);
    try { setMensaje((await authApi.restablecer(token, password)).mensaje); }
    catch (err) { setError(err instanceof Error ? err.message : 'No se pudo cambiar la contraseña.'); }
    finally { setEnviando(false); }
  }

  return (
    <div className="oscura pantalla-sin-nav">
      <h1 style={{ fontSize: 26, margin: '28px 0 6px' }}>Nueva contraseña</h1>
      {!token ? (
        <div className="stack" style={{ marginTop: 18 }}>
          <Aviso>Este enlace no es válido. Pide uno nuevo.</Aviso>
          <Link to="/recuperar" className="btn btn-neon">Pedir otro enlace</Link>
        </div>
      ) : mensaje ? (
        <div className="stack" style={{ marginTop: 18 }}>
          <Aviso tipo="ok">{mensaje}</Aviso>
          <Link to="/login" className="btn btn-neon">Ir a entrar</Link>
        </div>
      ) : (
        <form className="stack" style={{ marginTop: 18 }} onSubmit={enviar} noValidate>
          {error && <Aviso>{error} <Link to="/recuperar" style={{ color: 'inherit', fontWeight: 700 }}>Pedir otro enlace</Link></Aviso>}
          <Campo etiqueta="Nueva contraseña" type="password" autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)}
            ayuda="Mínimo 8 caracteres, con al menos una letra y un número." required />
          <button className="btn btn-neon" disabled={enviando || !pwOk}>{enviando ? 'Guardando…' : 'Guardar contraseña'}</button>
        </form>
      )}
    </div>
  );
}
