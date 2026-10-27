import { useEffect, useState } from 'react';
import { IconSearch } from '../components/Icons';
import ModalFichaEjercicio from '../components/ModalFichaEjercicio';
import { Aviso, Volver } from '../components/UI';
import { catalogoApi } from '../lib/endpoints';
import type { EjercicioResumen, GrupoMuscular } from '../lib/tipos';

const DIFICULTAD_TEXTO: Record<string, string> = {
  facil: 'Fácil',
  media: 'Media',
  dificil: 'Difícil',
};

export default function CatalogoEjercicios() {
  const [ejercicios, setEjercicios] = useState<EjercicioResumen[]>([]);
  const [grupos, setGrupos] = useState<GrupoMuscular[]>([]);
  const [grupoSel, setGrupoSel] = useState('');
  const [categoriaSel, setCategoriaSel] = useState('');
  const [q, setQ] = useState('');
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ejercicioSeleccionadoId, setEjercicioSeleccionadoId] = useState<number | null>(null);

  useEffect(() => {
    catalogoApi.grupos().then(setGrupos).catch(() => {});
  }, []);

  useEffect(() => {
    setCargando(true);
    catalogoApi.ejercicios({
      grupo: grupoSel || undefined,
      categoria: categoriaSel || undefined,
    })
      .then(r => { setEjercicios(r); setError(null); })
      .catch(e => setError(e instanceof Error ? e.message : 'No se pudieron cargar los ejercicios.'))
      .finally(() => setCargando(false));
  }, [grupoSel, categoriaSel]);

  const filtrados = ejercicios.filter(e => {
    if (!q.trim()) return true;
    const term = q.toLowerCase();
    return e.nombre.toLowerCase().includes(term) ||
      (e.musculo_principal?.toLowerCase().includes(term) ?? false) ||
      e.maquinas.some(m => m.nombre.toLowerCase().includes(term));
  });

  return (
    <div className="pantalla stack" style={{ gap: 16 }}>
      <header className="stack" style={{ gap: 4 }}>
        <h1 style={{ fontSize: 24 }}>Catálogo de Ejercicios</h1>
        <p className="muted" style={{ fontSize: 14 }}>
          Toca cualquier ejercicio para ver su mapa muscular anatómico y técnica detallada.
        </p>
      </header>

      {/* Buscador */}
      <div style={{ position: 'relative' }}>
        <IconSearch width={18} height={18} style={{ position: 'absolute', left: 14, top: 15, color: 'var(--muted)' }} />
        <input
          className="input"
          style={{ paddingLeft: 40 }}
          type="search"
          placeholder="Buscar ejercicio o máquina…"
          value={q}
          onChange={e => setQ(e.target.value)}
          aria-label="Buscar ejercicio"
        />
      </div>

      {/* Filtro por grupo muscular */}
      <div className="chips" role="group" aria-label="Filtrar por grupo muscular">
        <button type="button" className="chip" aria-pressed={grupoSel === ''} onClick={() => setGrupoSel('')}>Todos</button>
        {grupos.map(g => (
          <button type="button" key={g.codigo} className="chip" aria-pressed={grupoSel === g.codigo} onClick={() => setGrupoSel(g.codigo)}>
            {g.nombre}
          </button>
        ))}
      </div>

      {/* Filtro por categoría de equipo */}
      <div className="fila" style={{ gap: 6, flexWrap: 'wrap' }}>
        <button
          type="button"
          className="chip"
          aria-pressed={categoriaSel === ''}
          onClick={() => setCategoriaSel('')}
          style={{ fontSize: 12.5 }}
        >
          Cualquier equipo
        </button>
        <button
          type="button"
          className="chip"
          aria-pressed={categoriaSel === 'maquina'}
          onClick={() => setCategoriaSel('maquina')}
          style={{ fontSize: 12.5 }}
        >
          Máquinas guiadas
        </button>
        <button
          type="button"
          className="chip"
          aria-pressed={categoriaSel === 'peso_libre'}
          onClick={() => setCategoriaSel('peso_libre')}
          style={{ fontSize: 12.5 }}
        >
          Peso libre
        </button>
        <button
          type="button"
          className="chip"
          aria-pressed={categoriaSel === 'sin_equipo'}
          onClick={() => setCategoriaSel('sin_equipo')}
          style={{ fontSize: 12.5 }}
        >
          Sin equipo
        </button>
      </div>

      {error && <Aviso>{error}</Aviso>}
      {cargando && <p className="muted" style={{ textAlign: 'center', padding: 16 }}>Cargando ejercicios…</p>}

      {!cargando && filtrados.length === 0 && (
        <p className="muted" style={{ textAlign: 'center', padding: 24 }}>
          No se encontraron ejercicios con estos filtros.
        </p>
      )}

      {/* Lista de ejercicios */}
      <div className="stack" style={{ gap: 10 }}>
        {filtrados.map(e => (
          <button
            key={e.id}
            type="button"
            className="card fila"
            onClick={() => setEjercicioSeleccionadoId(e.id)}
            style={{
              textAlign: 'left',
              gap: 12,
              alignItems: 'center',
              cursor: 'pointer',
              border: '1px solid var(--border)',
            }}
          >
            <div className="stack" style={{ gap: 4, flex: 1, minWidth: 0 }}>
              <b style={{ fontSize: 15 }}>{e.nombre}</b>
              <div className="fila" style={{ gap: 6, flexWrap: 'wrap', fontSize: 12 }}>
                <span className="chip" style={{ fontSize: 11, padding: '2px 8px', background: 'var(--primary-tint)', color: 'var(--primary-dark)', fontWeight: 600 }}>
                  {e.musculo_principal ?? 'Varios'}
                </span>
                <span className="muted">· Dificultad: {DIFICULTAD_TEXTO[e.dificultad] ?? e.dificultad}</span>
                {e.maquinas.length > 0 && (
                  <span className="muted">· {e.maquinas[0].nombre}</span>
                )}
              </div>
            </div>
            <span style={{ fontSize: 18, color: 'var(--muted)' }}>›</span>
          </button>
        ))}
      </div>

      {/* MODAL DE FICHA TÉCNICA Y MAPA ANATÓMICO */}
      {ejercicioSeleccionadoId !== null && (
        <ModalFichaEjercicio
          ejercicioId={ejercicioSeleccionadoId}
          onCerrar={() => setEjercicioSeleccionadoId(null)}
        />
      )}
    </div>
  );
}
