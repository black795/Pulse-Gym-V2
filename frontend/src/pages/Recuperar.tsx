import { useState, type FormEvent } from 'react';
import { Aviso, Campo, Volver } from '../components/UI';
import { authApi } from '../lib/endpoints';

export default function Recuperar() {
  const [email, setEmail] = useState('');
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError(null); setEnviando(true);
    try { setMensaje((await authApi.recuperar(email.trim())).mensaje); }
    catch (err) { setError(err instanceof Error ? err.message : 'No se pudo enviar el correo.'); }
    finally { setEnviando(false); }
  }

  return (
    <div className="oscura pantalla-sin-nav">
      <Volver a="/login" texto="Volver a entrar" />
      <h1 style={{ fontSize: 26, margin: '18px 0 6px' }}>Recupera tu contraseña</h1>
      <p className="muted" style={{ marginBottom: 24 }}>Te enviamos un enlace al correo. Dura 30 minutos y solo sirve una vez.</p>
      {mensaje ? <Aviso tipo="ok">{mensaje}</Aviso> : (
        <form className="stack" onSubmit={enviar} noValidate>
          {error && <Aviso>{error}</Aviso>}
          <Campo etiqueta="Correo de tu cuenta" type="email" autoComplete="email" inputMode="email" value={email} onChange={e => setEmail(e.target.value)} required />
          <button className="btn btn-neon" disabled={enviando || !email}>{enviando ? 'Enviando…' : 'Enviarme el enlace'}</button>
        </form>
      )}
    </div>
  );
}
