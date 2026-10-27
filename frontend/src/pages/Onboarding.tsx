/** PG-02: perfil en máximo 3 pantallas. Cada pantalla guarda lo suyo, así no se pierde nada si cierras la app. */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { Aviso, Campo, Opciones, Volver, aNumero } from '../components/UI';
import { ApiError } from '../lib/http';
import { perfilApi } from '../lib/endpoints';
import type { PerfilEnvio } from '../lib/tipos';
import { NIVELES, OBJETIVOS, SEXOS, usePerfil } from '../lib/usePerfil';

const texto = (n: number | null | undefined) => (n == null ? '' : String(n));

export default function Onboarding() {
  const nav = useNavigate();
  const { perfil } = usePerfil();
  const [paso, setPaso] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [f, setF] = useState({
    edad: '', sexo: '', peso: '', altura: '', grasa: '', masa: '',
    objetivo: '', nivel: '', dias: '', minutos: '',
  });
  const poner = (k: keyof typeof f, v: string) => setF(p => ({ ...p, [k]: v }));

  // Si ya había datos guardados, se muestran en vez de empezar en blanco.
  useEffect(() => {
    if (!perfil) return;
    setF(p => ({
      ...p, edad: p.edad || texto(perfil.edad), sexo: p.sexo || (perfil.sexo ?? ''), altura: p.altura || texto(perfil.altura_cm),
      peso: p.peso || texto(perfil.ultima_medicion?.peso_kg), grasa: p.grasa || texto(perfil.ultima_medicion?.grasa_pct),
      masa: p.masa || texto(perfil.ultima_medicion?.masa_muscular_kg), objetivo: p.objetivo || (perfil.objetivo ?? ''),
      nivel: p.nivel || (perfil.nivel ?? ''), dias: p.dias || texto(perfil.dias_por_semana), minutos: p.minutos || texto(perfil.minutos_por_sesion),
    }));
  }, [perfil]);

  const rechazado = perfil?.consentimiento.estado === 'rechazado';

  // PG-05: el permiso se pide ANTES de preguntar peso y altura, para que nadie pierda lo que escribió.
  useEffect(() => {
    if (perfil?.consentimiento.estado === 'pendiente') nav('/consentimiento?volver=/onboarding', { replace: true });
  }, [perfil, nav]);

  async function guardar(datos: PerfilEnvio, siguiente: () => void) {
    setError(null); setEnviando(true);
    try { await perfilApi.guardar(datos); siguiente(); }
    catch (e) {
      if (e instanceof ApiError && e.codigo === 'consentimiento_requerido') nav('/consentimiento?volver=/onboarding');
      else setError(e instanceof Error ? e.message : 'No se pudo guardar.');
    } finally { setEnviando(false); }
  }

  const paso1 = () => {
    const d: PerfilEnvio = { edad: aNumero(f.edad), sexo: f.sexo || undefined };
    if (!rechazado) { d.peso_kg = aNumero(f.peso); d.altura_cm = aNumero(f.altura); }
    return guardar(clean(d), () => setPaso(2));
  };
  const paso2 = () => {
    const d = clean({ grasa_pct: aNumero(f.grasa), masa_muscular_kg: aNumero(f.masa) });
    return Object.keys(d).length ? guardar(d, () => setPaso(3)) : setPaso(3);
  };
  const paso3 = () => guardar(
    clean({ objetivo: f.objetivo || undefined, nivel: f.nivel || undefined, dias_por_semana: aNumero(f.dias), minutos_por_sesion: aNumero(f.minutos) }),
    () => nav('/', { replace: true }),
  );

  const ok1 = !!aNumero(f.edad) && !!f.sexo && (rechazado || (!!aNumero(f.peso) && !!aNumero(f.altura)));
  const ok3 = !!f.objetivo && !!f.nivel && !!aNumero(f.dias) && !!aNumero(f.minutos);

  return (
    <div className="pantalla-sin-nav stack" style={{ gap: 18 }}>
      <div className="fila" style={{ justifyContent: 'space-between' }}>
        {paso === 1 ? <Volver a="/" texto="Después" /> : <button className="btn btn-texto" onClick={() => setPaso(paso - 1)}>← Atrás</button>}
        <span className="muted" style={{ fontSize: 13, fontWeight: 700 }}>Paso {paso} de 3</span>
      </div>
      <div className="barra-progreso" aria-hidden>{[1, 2, 3].map(n => <span key={n} className={n <= paso ? 'on' : ''} />)}</div>
      {error && <Aviso>{error}</Aviso>}

      {paso === 1 && (
        <div className="stack">
          <h1 style={{ fontSize: 24 }}>Cuéntanos de ti</h1>
          <p className="muted">Con esto calculamos tu punto de partida.</p>
          <Campo etiqueta="Edad" inputMode="numeric" value={f.edad} onChange={e => poner('edad', e.target.value)} ayuda="Entre 16 y 90 años." />
          <div className="campo"><label>Sexo</label><Opciones columnas={3} valor={f.sexo} onCambio={v => poner('sexo', v)} opciones={SEXOS} /></div>
          {rechazado
            ? <Aviso tipo="info">No aceptaste guardar datos de salud, así que omitimos peso y altura. Puedes cambiarlo cuando quieras en Perfil → Privacidad.</Aviso>
            : <div className="grid-2">
                <Campo etiqueta="Peso (kg)" inputMode="decimal" value={f.peso} onChange={e => poner('peso', e.target.value)} />
                <Campo etiqueta="Altura (cm)" inputMode="decimal" value={f.altura} onChange={e => poner('altura', e.target.value)} />
              </div>}
          <button className="btn" disabled={!ok1 || enviando} onClick={paso1}>{enviando ? 'Guardando…' : 'Siguiente'}</button>
        </div>
      )}

      {paso === 2 && (
        <div className="stack">
          <h1 style={{ fontSize: 24 }}>Composición corporal</h1>
          <p className="muted">Opcional. Si no lo sabes, salta este paso: puedes agregarlo después desde tu perfil.</p>
          {rechazado
            ? <Aviso tipo="info">Estos datos son de salud; como no diste tu consentimiento, no se guardan.</Aviso>
            : <div className="grid-2">
                <Campo etiqueta="% de grasa" inputMode="decimal" value={f.grasa} onChange={e => poner('grasa', e.target.value)} ayuda="Entre 3 y 60." />
                <Campo etiqueta="Masa muscular (kg)" inputMode="decimal" value={f.masa} onChange={e => poner('masa', e.target.value)} ayuda="Entre 10 y 150." />
              </div>}
          <button className="btn" disabled={enviando} onClick={paso2}>{rechazado || (!f.grasa && !f.masa) ? 'Saltar' : enviando ? 'Guardando…' : 'Siguiente'}</button>
        </div>
      )}

      {paso === 3 && (
        <div className="stack">
          <h1 style={{ fontSize: 24 }}>Tu meta y tu tiempo</h1>
          <div className="campo"><label>¿Cuál es tu objetivo?</label><Opciones valor={f.objetivo} onCambio={v => poner('objetivo', v)} opciones={OBJETIVOS} /></div>
          <div className="campo"><label>¿Qué nivel tienes?</label><Opciones valor={f.nivel} onCambio={v => poner('nivel', v)} opciones={NIVELES} /></div>
          <div className="grid-2">
            <Campo etiqueta="Días por semana" inputMode="numeric" value={f.dias} onChange={e => poner('dias', e.target.value)} ayuda="De 1 a 7." />
            <Campo etiqueta="Minutos por sesión" inputMode="numeric" value={f.minutos} onChange={e => poner('minutos', e.target.value)} ayuda="De 20 a 180." />
          </div>
          <button className="btn" disabled={!ok3 || enviando} onClick={paso3}>{enviando ? 'Guardando…' : 'Terminar'}</button>
        </div>
      )}
    </div>
  );
}

/** Quita los campos vacíos para no mandar "undefined" ni borrar datos sin querer. */
function clean<T extends object>(o: T): T {
  return Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined && v !== '')) as T;
}
