/** PG-05: se muestra antes de guardar datos sensibles (peso, medidas, lesiones). Aceptar o no aceptar, la persona decide. */
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { Aviso } from '../components/UI';
import { IconLock } from '../components/Icons';
import { useAuth } from '../features/auth/AuthContext';
import { perfilApi } from '../lib/endpoints';
import type { TextoConsentimiento } from '../lib/tipos';

export default function Consentimiento() {
  const nav = useNavigate();
  const { refrescar } = useAuth();
  const volver = useSearchParams()[0].get('volver') ?? '/';
  const destino = volver.startsWith('/') && !volver.startsWith('//') ? volver : '/';
  const [texto, setTexto] = useState<TextoConsentimiento | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => { perfilApi.textoConsentimiento().then(setTexto).catch(e => setError(e.message)); }, []);

  async function decidir(acepta: boolean) {
    setError(null); setEnviando(true);
    try { await perfilApi.fijarConsentimiento(acepta); await refrescar(); nav(destino, { replace: true }); }
    catch (e) { setError(e instanceof Error ? e.message : 'No se pudo guardar tu decisión.'); setEnviando(false); }
  }

  return (
    <div className="pantalla-sin-nav stack" style={{ gap: 18 }}>
      <div style={{ width: 52, height: 52, borderRadius: 14, background: 'var(--primary-tint)', display: 'grid', placeItems: 'center', color: 'var(--primary-dark)' }}>
        <IconLock width={26} height={26} />
      </div>
      <h1 style={{ fontSize: 24 }}>{texto?.titulo ?? 'Tus datos de salud'}</h1>
      {error && <Aviso>{error}</Aviso>}
      {texto?.secciones.map(s => (
        <section key={s.titulo}>
          <h2 style={{ fontSize: 15, marginBottom: 4 }}>{s.titulo}</h2>
          <p className="muted" style={{ fontSize: 14.5, lineHeight: 1.5 }}>{s.texto}</p>
        </section>
      ))}
      <div className="stack" style={{ marginTop: 6 }}>
        <button className="btn" disabled={!texto || enviando} onClick={() => decidir(true)}>Acepto, guardar mis datos</button>
        <button className="btn btn-claro" disabled={!texto || enviando} onClick={() => decidir(false)}>No, gracias</button>
      </div>
      {texto && <p className="muted" style={{ fontSize: 12, textAlign: 'center' }}>Versión del texto: {texto.version}</p>}
    </div>
  );
}
