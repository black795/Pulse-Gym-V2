/** PG-09: siempre existe la opción de buscar a mano en el catálogo, por nombre o por músculo. */
import { useEffect, useState } from 'react';
import { IconSearch } from './Icons';
import { Aviso } from './UI';
import { catalogoApi } from '../lib/endpoints';
import type { GrupoMuscular, MaquinaCatalogo } from '../lib/tipos';

export default function BuscadorMaquinas({ onElegir, ocupado }: { onElegir: (m: MaquinaCatalogo) => void; ocupado?: boolean }) {
  const [q, setQ] = useState('');
  const [grupo, setGrupo] = useState('');
  const [grupos, setGrupos] = useState<GrupoMuscular[]>([]);
  const [resultados, setResultados] = useState<MaquinaCatalogo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { catalogoApi.grupos().then(setGrupos).catch(() => {}); }, []);

  useEffect(() => {
    let activo = true;
    const t = setTimeout(() => {
      catalogoApi.maquinas({ q: q.trim() || undefined, grupo: grupo || undefined })
        .then(r => { if (activo) { setResultados(r); setError(null); } })
        .catch(e => activo && setError(e.message));
    }, 250); // espera a que termine de escribir
    return () => { activo = false; clearTimeout(t); };
  }, [q, grupo]);

  return (
    <div className="stack" style={{ gap: 12 }}>
      <div style={{ position: 'relative' }}>
        <IconSearch width={18} height={18} style={{ position: 'absolute', left: 14, top: 15, color: 'var(--muted)' }} />
        <input className="input" style={{ paddingLeft: 40 }} type="search" placeholder="Ej. prensa, polea, leg press…"
          value={q} onChange={e => setQ(e.target.value)} aria-label="Buscar máquina por nombre" />
      </div>
      <div className="chips" role="group" aria-label="Filtrar por músculo">
        <button type="button" className="chip" aria-pressed={grupo === ''} onClick={() => setGrupo('')}>Todos</button>
        {grupos.map(g => (
          <button type="button" key={g.codigo} className="chip" aria-pressed={grupo === g.codigo} onClick={() => setGrupo(g.codigo)}>{g.nombre}</button>
        ))}
      </div>
      {error && <Aviso>{error}</Aviso>}
      {resultados && resultados.length === 0 && <p className="muted" style={{ textAlign: 'center', padding: 8 }}>No encontramos máquinas con esa búsqueda.</p>}
      {resultados?.map(m => (
        <button key={m.codigo} type="button" className="opcion-maquina" disabled={ocupado} onClick={() => onElegir(m)}>
          {m.fotos[0] ? <img className="miniatura" src={m.fotos[0]} alt="" loading="lazy" /> : <span className="miniatura" />}
          <span>
            <b style={{ display: 'block', fontSize: 15 }}>{m.nombre}</b>
            <span className="muted" style={{ fontSize: 13 }}>{m.musculo_principal ?? 'Varios músculos'}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
