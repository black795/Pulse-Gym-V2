/**
 * PG-09: el usuario confirma lo que reconoció la IA o elige la correcta.
 * - Confianza alta (≥ 0,85): solo confirma.
 * - Media o baja: elige entre 2–3 parecidas (nombre, foto de referencia y músculo principal).
 * - «Ninguna es» y «Buscar a mano» siempre disponibles. Nada entra al inventario sin confirmar.
 * PG-12: si la máquina ya estaba en el gym, avisa y ofrece actualizar su foto.
 */
import { useState } from 'react';
import BuscadorMaquinas from './BuscadorMaquinas';
import { IconCheck, IconSearch, IconX } from './Icons';
import { Aviso, Insignia } from './UI';
import { fotosApi } from '../lib/endpoints';
import { ApiError } from '../lib/http';
import type { MaquinaOpcion, Reconocimiento } from '../lib/tipos';

type Paso = 'ia' | 'no_maquina' | 'buscar';
type Eleccion = { codigo: string; nombre: string; origen: 'sugerencia' | 'manual' };

const pct = (c: number) => `${Math.round(c * 100)}%`;

export default function RevisarFoto({ fotoId, vista, rec, onHecho, onDescartada, onCerrar }: {
  fotoId: number;
  vista: string; // foto tomada (URL local)
  rec: Reconocimiento | null; // null = la IA falló y el usuario eligió buscar a mano
  onHecho: (mensaje: string) => void;
  onDescartada: () => void;
  onCerrar: () => void;
}) {
  const inicial: Paso = !rec ? 'buscar' : !rec.es_maquina_de_gym ? 'no_maquina' : rec.sugerencias.length ? 'ia' : 'buscar';
  const [paso, setPaso] = useState<Paso>(inicial);
  const [verOtras, setVerOtras] = useState(false);
  const [elegida, setElegida] = useState<string | null>(null);
  const [duplicada, setDuplicada] = useState<Eleccion | null>(null);
  const [nota, setNota] = useState<string | null>(rec && rec.es_maquina_de_gym && !rec.sugerencias.length ? 'La IA no encontró una máquina parecida en el catálogo. Búscala a mano.' : null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function confirmar(e: Eleccion, reemplazar = false) {
    setOcupado(true); setError(null);
    try {
      const r = await fotosApi.confirmar(fotoId, { codigo: e.codigo, origen: e.origen, reemplazar_foto: reemplazar });
      onHecho(r.accion === 'agregada' ? `${e.nombre} se agregó a tu gym.` : `Se actualizó la foto de ${e.nombre}.`);
    } catch (err) {
      if (err instanceof ApiError && err.codigo === 'ya_en_inventario') setDuplicada(e);
      else setError(err instanceof Error ? err.message : 'No se pudo agregar.');
    } finally { setOcupado(false); }
  }

  async function descartar() {
    setOcupado(true);
    try { await fotosApi.descartar(fotoId); onDescartada(); }
    catch (err) { setError(err instanceof Error ? err.message : 'No se pudo descartar.'); setOcupado(false); }
  }

  async function ningunaEs() {
    setOcupado(true); setError(null);
    try {
      await fotosApi.ninguna(fotoId);
      setNota('Anotado. Pronto la buscaremos en internet por ti; por ahora puedes buscarla a mano en el catálogo.');
      setPaso('buscar');
    } catch (err) { setError(err instanceof Error ? err.message : 'No se pudo guardar.'); }
    finally { setOcupado(false); }
  }

  const sugerencias = rec?.sugerencias ?? [];
  const primera = sugerencias[0];
  const soloConfirmar = !!rec?.confianza_alta && !verOtras && !!primera;

  return (
    <div className="velo" onClick={onCerrar}>
      <section className="hoja stack" style={{ gap: 14 }} onClick={e => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="titulo-revisar">
        <div className="fila" style={{ justifyContent: 'space-between' }}>
          <h2 id="titulo-revisar" style={{ fontSize: 18 }}>
            {duplicada ? 'Ya está en tu gym' : paso === 'buscar' ? 'Buscar en el catálogo' : paso === 'no_maquina' ? 'Revisa la foto' : soloConfirmar ? '¿Es esta máquina?' : '¿Cuál de estas es?'}
          </h2>
          <button className="btn btn-texto" onClick={onCerrar} aria-label="Cerrar"><IconX /></button>
        </div>
        <img className="miniatura-grande" src={vista} alt="Tu foto" style={{ aspectRatio: '16 / 9' }} />
        {error && <Aviso>{error}</Aviso>}

        {duplicada ? (
          <>
            <Aviso tipo="info"><b>{duplicada.nombre}</b> ya está en el inventario de este gym (se registra una sola vez aunque haya varias). ¿Quieres usar esta foto nueva?</Aviso>
            <button className="btn" disabled={ocupado} onClick={() => confirmar(duplicada, true)}>Sí, actualizar su foto</button>
            <button className="btn btn-claro" disabled={ocupado} onClick={descartar}>No, dejar la anterior</button>
          </>
        ) : paso === 'no_maquina' ? (
          <>
            <Aviso tipo="info">No parece una máquina de gym. Toma otra foto con la máquina completa y bien iluminada.</Aviso>
            <button className="btn" disabled={ocupado} onClick={descartar}>Tomar otra foto</button>
            <button className="btn btn-claro" onClick={() => setPaso('buscar')}><IconSearch width={18} height={18} /> Sí es una máquina: buscarla a mano</button>
          </>
        ) : paso === 'buscar' ? (
          <>
            {nota && <Aviso tipo="info">{nota}</Aviso>}
            <BuscadorMaquinas ocupado={ocupado} onElegir={m => confirmar({ codigo: m.codigo, nombre: m.nombre, origen: 'manual' })} />
            {rec && rec.sugerencias.length > 0 && <button className="btn btn-texto" style={{ alignSelf: 'center' }} onClick={() => { setPaso('ia'); setNota(null); }}>Volver a las sugerencias</button>}
          </>
        ) : soloConfirmar ? (
          <>
            <OpcionMaquina m={primera.maquina} confianza={primera.confianza} yaEsta={primera.ya_en_inventario} />
            <button className="btn" disabled={ocupado} onClick={() => confirmar({ codigo: primera.maquina.codigo, nombre: primera.maquina.nombre, origen: 'sugerencia' })}>
              <IconCheck width={18} height={18} /> Sí, agregar a mi gym
            </button>
            <button className="btn btn-claro" onClick={() => setVerOtras(true)}>No, es otra</button>
          </>
        ) : (
          <>
            <p className="muted" style={{ fontSize: 14 }}>La IA no está segura. Toca la que corresponde:</p>
            <div className="stack" style={{ gap: 8 }} role="radiogroup">
              {sugerencias.map(s => (
                <OpcionMaquina key={s.maquina.codigo} m={s.maquina} confianza={s.confianza} yaEsta={s.ya_en_inventario}
                  elegida={elegida === s.maquina.codigo} onElegir={() => setElegida(s.maquina.codigo)} />
              ))}
            </div>
            <button className="btn" disabled={!elegida || ocupado} onClick={() => {
              const s = sugerencias.find(x => x.maquina.codigo === elegida)!;
              void confirmar({ codigo: s.maquina.codigo, nombre: s.maquina.nombre, origen: 'sugerencia' });
            }}>Agregar a mi gym</button>
            <button className="btn btn-claro" disabled={ocupado} onClick={ningunaEs}>Ninguna es</button>
          </>
        )}

        {!duplicada && paso === 'ia' && (
          <button className="btn btn-texto" style={{ alignSelf: 'center' }} onClick={() => setPaso('buscar')}>
            <IconSearch width={16} height={16} /> Buscar a mano por nombre o músculo
          </button>
        )}
        {!duplicada && paso !== 'no_maquina' && (
          <button className="btn btn-texto" style={{ alignSelf: 'center', color: 'var(--danger)' }} disabled={ocupado} onClick={descartar}>Descartar esta foto</button>
        )}
        {rec && <p className="muted" style={{ fontSize: 11.5, textAlign: 'center' }}>IA: {rec.modelo} · {(rec.duracion_ms / 1000).toFixed(1)} s</p>}
      </section>
    </div>
  );
}

function OpcionMaquina({ m, confianza, yaEsta, elegida, onElegir }: {
  m: MaquinaOpcion; confianza: number; yaEsta: boolean; elegida?: boolean; onElegir?: () => void;
}) {
  const contenido = (
    <>
      {m.foto_ref ? <img className="miniatura" style={{ width: 72, height: 72 }} src={m.foto_ref} alt="" loading="lazy" /> : <span className="miniatura" style={{ width: 72, height: 72 }} />}
      <span className="stack" style={{ gap: 4, flex: 1 }}>
        <b style={{ fontSize: 15.5 }}>{m.nombre}</b>
        <span className="muted" style={{ fontSize: 13 }}>{m.musculo_principal ?? 'Varios músculos'}</span>
        <span className="fila" style={{ gap: 6, flexWrap: 'wrap' }}>
          <Insignia tono={confianza >= 0.85 ? 'ok' : confianza >= 0.5 ? 'aviso' : 'neutro'}>{pct(confianza)} de confianza</Insignia>
          {yaEsta && <Insignia tono="neutro">Ya está en tu gym</Insignia>}
        </span>
      </span>
    </>
  );
  return onElegir
    ? <button type="button" role="radio" aria-checked={elegida} aria-pressed={elegida} className="opcion-maquina" onClick={onElegir}>{contenido}</button>
    : <div className="opcion-maquina" style={{ cursor: 'default' }}>{contenido}</div>;
}
