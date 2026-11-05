/** PG-19: lesiones y limitaciones. Una lesión activa o en reintroducción limita los ejercicios que se proponen. */
import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';
import MapaMuscular from '../components/MapaMuscular';
import { Aviso, Insignia } from '../components/UI';
import { IconPlus } from '../components/Icons';
import { ApiError } from '../lib/http';
import { lesionesApi } from '../lib/endpoints';
import type { Lesion, LesionesRespuesta, Zona } from '../lib/tipos';
import { Opciones } from '../components/UI';

const ESTADOS = { activa: 'Activa', reintroduccion: 'Volviendo a entrenar', recuperada: 'Recuperada' } as const;
const TONO = { activa: 'peligro', reintroduccion: 'aviso', recuperada: 'ok' } as const;
// Zona de lesión → grupo muscular más cercano del mapa (muñeca y cuello no tienen uno propio).
const GRUPO_DE_ZONA: Record<string, string> = {
  hombro: 'hombros', codo: 'triceps', espalda_alta: 'espalda', espalda_baja: 'espalda', cadera: 'gluteos', rodilla: 'cuadriceps', tobillo: 'pantorrillas',
};

export default function Lesiones() {
  const nav = useNavigate();
  const [datos, setDatos] = useState<LesionesRespuesta | null>(null);
  const [zonas, setZonas] = useState<Zona[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [nueva, setNueva] = useState({ zona: '', tipo: 'aguda' as 'aguda' | 'cronica', duele: false, descripcion: '' });
  const [enviando, setEnviando] = useState(false);

  const cargar = useCallback(() => lesionesApi.listar().then(setDatos).catch(e => setError(e.message)), []);
  useEffect(() => { void cargar(); lesionesApi.zonas().then(setZonas).catch(() => {}); }, [cargar]);

  const pedirConsentimiento = (e: unknown) => {
    if (e instanceof ApiError && e.codigo === 'consentimiento_requerido') { nav('/consentimiento?volver=/lesiones'); return true; }
    return false;
  };

  async function agregar(ev: FormEvent) {
    ev.preventDefault();
    setError(null); setEnviando(true);
    try {
      await lesionesApi.crear({ zona: nueva.zona, tipo: nueva.tipo, duele_con_carga: nueva.duele, descripcion: nueva.descripcion.trim() || undefined });
      setNueva({ zona: '', tipo: 'aguda', duele: false, descripcion: '' }); setAbierto(false); await cargar();
    } catch (e) { if (!pedirConsentimiento(e)) setError(e instanceof Error ? e.message : 'No se pudo guardar.'); }
    finally { setEnviando(false); }
  }

  async function cambiarEstado(l: Lesion, estado: Lesion['estado']) {
    setError(null);
    try { await lesionesApi.cambiar(l.id, { estado }); await cargar(); }
    catch (e) { if (!pedirConsentimiento(e)) setError(e instanceof Error ? e.message : 'No se pudo cambiar el estado.'); }
  }

  const vigentes = datos?.lesiones.filter(l => l.estado !== 'recuperada') ?? [];
  const recuperadas = datos?.lesiones.filter(l => l.estado === 'recuperada') ?? [];
  const gruposLesionados = [...new Set(vigentes.map(l => GRUPO_DE_ZONA[l.zona.codigo]).filter(Boolean))];
  const nuevaEn = (zona: string) => { setNueva(p => ({ ...p, zona })); setAbierto(true); };

  return (
    <div className="pantalla stack" style={{ gap: 16 }}>
      <h1 style={{ fontSize: 24, paddingTop: 8 }}>Lesiones</h1>
      <p className="muted" style={{ fontSize: 14 }}>Si algo te duele, dínoslo: evitamos los ejercicios que lo empeoran y buscamos reemplazos.</p>
      {datos && <Aviso tipo="info">{datos.aviso}</Aviso>}
      {error && <Aviso>{error}</Aviso>}

      <div className="columnas-escritorio columnas-lesiones">
        {/* Solo en escritorio: mapa del cuerpo con las zonas lesionadas y acceso directo por zona */}
        <aside className="card stack solo-escritorio columna-fija" style={{ gap: 14 }} aria-labelledby="mapa-lesiones">
          <div className="stack" style={{ gap: 4 }}>
            <h2 id="mapa-lesiones" style={{ fontSize: 17 }}>Tu cuerpo hoy</h2>
            <p className="muted" style={{ fontSize: 13.5 }}>
              {gruposLesionados.length ? 'En ámbar, las zonas que estamos cuidando en tu plan.' : 'Sin zonas lesionadas: tu plan no tiene restricciones.'}
            </p>
          </div>
          <MapaMuscular musculosSecundarios={gruposLesionados} textoSecundario="Cuidando" />
          {zonas.length > 0 && (
            <div className="stack" style={{ gap: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 700 }}>¿Te duele algo? Elige la zona</span>
              <div className="chips">
                {zonas.map(z => (
                  <button key={z.codigo} type="button" className="chip" aria-pressed={abierto && nueva.zona === z.codigo}
                    style={vigentes.some(l => l.zona.codigo === z.codigo) ? { borderColor: 'var(--warning)' } : undefined}
                    onClick={() => nuevaEn(z.codigo)}>{z.nombre}</button>
                ))}
              </div>
            </div>
          )}
        </aside>

        <div className="stack" style={{ gap: 16 }}>
          {!abierto && <button className="btn" onClick={() => setAbierto(true)}><IconPlus width={18} height={18} /> Agregar lesión</button>}
          {abierto && (
            <form className="card stack" onSubmit={agregar}>
              <h2 style={{ fontSize: 17 }}>Nueva lesión</h2>
              <div className="campo">
                <label htmlFor="zona">¿Dónde te duele?</label>
                <select id="zona" className="input" value={nueva.zona} onChange={e => setNueva(p => ({ ...p, zona: e.target.value }))} required>
                  <option value="">Elige una zona…</option>
                  {zonas.map(z => <option key={z.codigo} value={z.codigo}>{z.nombre}</option>)}
                </select>
              </div>
              <div className="campo"><label>Tipo</label>
                <Opciones columnas={2} valor={nueva.tipo} onCambio={v => setNueva(p => ({ ...p, tipo: v }))}
                  opciones={[{ valor: 'aguda', texto: 'Reciente (aguda)' }, { valor: 'cronica', texto: 'De hace tiempo (crónica)' }]} />
              </div>
              <div className="campo"><label>¿Te duele al cargar peso?</label>
                <Opciones columnas={2} valor={nueva.duele ? 'si' : 'no'} onCambio={v => setNueva(p => ({ ...p, duele: v === 'si' }))}
                  opciones={[{ valor: 'si', texto: 'Sí' }, { valor: 'no', texto: 'No' }]} />
              </div>
              <div className="campo"><label htmlFor="desc">Detalles (opcional)</label>
                <textarea id="desc" className="input" maxLength={300} value={nueva.descripcion} onChange={e => setNueva(p => ({ ...p, descripcion: e.target.value }))} />
              </div>
              <button className="btn" disabled={!nueva.zona || enviando}>{enviando ? 'Guardando…' : 'Guardar lesión'}</button>
              <button type="button" className="btn btn-texto" style={{ alignSelf: 'center' }} onClick={() => setAbierto(false)}>Cancelar</button>
            </form>
          )}

          {datos && vigentes.length === 0 && !abierto && <p className="muted" style={{ textAlign: 'center', padding: 12 }}>No tienes lesiones registradas. 💪</p>}
          {vigentes.map(l => <TarjetaLesion key={l.id} l={l} onCambio={cambiarEstado} />)}

          {recuperadas.length > 0 && (
            <>
              <h2 style={{ fontSize: 15, marginTop: 8 }}>Historial</h2>
              {recuperadas.map(l => <TarjetaLesion key={l.id} l={l} onCambio={cambiarEstado} />)}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function TarjetaLesion({ l, onCambio }: { l: Lesion; onCambio: (l: Lesion, e: Lesion['estado']) => void }) {
  return (
    <div className="card stack" style={{ gap: 10 }}>
      <div className="fila" style={{ justifyContent: 'space-between' }}>
        <h3 style={{ fontSize: 16 }}>{l.zona.nombre}</h3>
        <Insignia tono={TONO[l.estado]}>{ESTADOS[l.estado]}</Insignia>
      </div>
      <p className="muted" style={{ fontSize: 13.5 }}>
        {l.tipo === 'aguda' ? 'Reciente' : 'Crónica'}{l.duele_con_carga ? ' · duele al cargar peso' : ''}
        {l.descripcion ? ` · ${l.descripcion}` : ''}
      </p>
      <div className="fila" style={{ flexWrap: 'wrap' }}>
        {l.estado === 'activa' && <button className="btn btn-claro" style={{ width: 'auto', minHeight: 44 }} onClick={() => onCambio(l, 'reintroduccion')}>Ya puedo volver a entrenar</button>}
        {l.estado !== 'recuperada' && <button className="btn btn-claro" style={{ width: 'auto', minHeight: 44 }} onClick={() => onCambio(l, 'recuperada')}>Ya me recuperé</button>}
        {l.estado === 'recuperada' && <button className="btn btn-claro" style={{ width: 'auto', minHeight: 44 }} onClick={() => onCambio(l, 'activa')}>Me volvió a doler</button>}
      </div>
    </div>
  );
}
