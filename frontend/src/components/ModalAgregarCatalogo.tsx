import { useEffect, useState } from 'react';
import { IconCheck, IconPlus, IconSearch } from './Icons';
import { Aviso } from './UI';
import { catalogoApi } from '../lib/endpoints';
import type { GrupoMuscular, MaquinaCatalogo } from '../lib/tipos';

interface Props {
  gymId: number;
  codigosExistentes: string[];
  onAgregar: (maquina: MaquinaCatalogo) => Promise<void>;
  onCerrar: () => void;
}

export default function ModalAgregarCatalogo({ gymId, codigosExistentes, onAgregar, onCerrar }: Props) {
  const [q, setQ] = useState('');
  const [grupo, setGrupo] = useState('');
  const [grupos, setGrupos] = useState<GrupoMuscular[]>([]);
  const [resultados, setResultados] = useState<MaquinaCatalogo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agregandoCodigo, setAgregandoCodigo] = useState<string | null>(null);

  useEffect(() => {
    catalogoApi.grupos().then(setGrupos).catch(() => {});
  }, []);

  useEffect(() => {
    let activo = true;
    const t = setTimeout(() => {
      catalogoApi.maquinas({ q: q.trim() || undefined, grupo: grupo || undefined })
        .then(r => { if (activo) { setResultados(r); setError(null); } })
        .catch(e => activo && setError(e.message));
    }, 200);
    return () => { activo = false; clearTimeout(t); };
  }, [q, grupo]);

  async function handleAgregar(m: MaquinaCatalogo) {
    setAgregandoCodigo(m.codigo);
    setError(null);
    try {
      await onAgregar(m);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo agregar la máquina.');
    } finally {
      setAgregandoCodigo(null);
    }
  }

  const codigosSet = new Set(codigosExistentes.map(c => c.toUpperCase()));

  return (
    <div className="velo" role="dialog" aria-modal="true" onClick={onCerrar}>
      <div className="hoja stack" style={{ gap: 14 }} onClick={e => e.stopPropagation()}>
        <div className="fila" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: 18 }}>Agregar desde el catálogo</h2>
            <p className="muted" style={{ fontSize: 13 }}>Busca la máquina por nombre o filtra por grupo muscular</p>
          </div>
          <button className="btn btn-texto" onClick={onCerrar} style={{ fontSize: 18, padding: '4px 8px' }}>✕</button>
        </div>

        {/* Buscador de texto */}
        <div style={{ position: 'relative' }}>
          <IconSearch width={18} height={18} style={{ position: 'absolute', left: 14, top: 15, color: 'var(--muted)' }} />
          <input
            className="input"
            style={{ paddingLeft: 40 }}
            type="search"
            placeholder="Ej. péndulo, prensa, polea, hack…"
            value={q}
            onChange={e => setQ(e.target.value)}
            aria-label="Buscar máquina por nombre"
            autoFocus
          />
        </div>

        {/* Chips de filtro por grupo muscular */}
        <div className="chips" role="group" aria-label="Filtrar por músculo">
          <button type="button" className="chip" aria-pressed={grupo === ''} onClick={() => setGrupo('')}>Todos</button>
          {grupos.map(g => (
            <button type="button" key={g.codigo} className="chip" aria-pressed={grupo === g.codigo} onClick={() => setGrupo(g.codigo)}>
              {g.nombre}
            </button>
          ))}
        </div>

        {error && <Aviso>{error}</Aviso>}

        {resultados && resultados.length === 0 && (
          <p className="muted" style={{ textAlign: 'center', padding: 16 }}>No se encontraron máquinas con esa búsqueda.</p>
        )}

        {/* Lista de máquinas */}
        <div className="stack" style={{ gap: 8, marginTop: 4 }}>
          {resultados?.map(m => {
            const yaEsta = codigosSet.has(m.codigo.toUpperCase());
            const ocupado = agregandoCodigo === m.codigo;
            return (
              <div
                key={m.codigo}
                className="card fila"
                style={{
                  padding: 10,
                  gap: 12,
                  alignItems: 'center',
                  background: yaEsta ? 'var(--bg)' : 'var(--surface)',
                  opacity: yaEsta ? 0.75 : 1,
                }}
              >
                {m.fotos[0] ? (
                  <img className="miniatura" src={m.fotos[0]} alt="" loading="lazy" />
                ) : (
                  <span className="miniatura" />
                )}
                <div className="stack" style={{ gap: 2, flex: 1, minWidth: 0 }}>
                  <b style={{ fontSize: 14.5 }}>{m.nombre}</b>
                  <span className="muted" style={{ fontSize: 12.5 }}>
                    {m.musculo_principal ?? 'Varios músculos'}
                    {m.otros_nombres.length > 0 && ` · ${m.otros_nombres.slice(0, 2).join(', ')}`}
                  </span>
                </div>
                <div>
                  {yaEsta ? (
                    <span className="chip" style={{ fontSize: 12, color: 'var(--primary-dark)', background: 'var(--primary-tint)' }}>
                      <IconCheck width={14} height={14} style={{ verticalAlign: -2, marginRight: 2 }} /> Ya agregada
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-claro"
                      style={{ fontSize: 13, padding: '6px 12px', minHeight: 34 }}
                      disabled={ocupado}
                      onClick={() => handleAgregar(m)}
                    >
                      {ocupado ? '…' : '+ Agregar'}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <button type="button" className="btn btn-claro" onClick={onCerrar} style={{ alignSelf: 'center', marginTop: 8 }}>
          Listo
        </button>
      </div>
    </div>
  );
}
