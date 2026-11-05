import { useEffect, useState } from 'react';
import { catalogoApi } from '../lib/endpoints';
import type { EjercicioFicha } from '../lib/tipos';
import MapaMuscular from './MapaMuscular';
import { IconAlertTriangle, IconCheck } from './Icons';
import { Aviso } from './UI';

interface Props {
  ejercicioId: number;
  onCerrar: () => void;
}

const DIFICULTAD_TEXTO: Record<string, string> = {
  facil: 'Fácil (Principiante)',
  media: 'Media (Intermedio)',
  dificil: 'Difícil (Avanzado)',
};

const CATEGORIA_TEXTO: Record<string, string> = {
  maquina: 'Máquina guiada / Polea',
  peso_libre: 'Peso libre (Barras / Mancuernas)',
  sin_equipo: 'Sin equipo / Peso corporal',
};

export default function ModalFichaEjercicio({ ejercicioId, onCerrar }: Props) {
  const [ficha, setFicha] = useState<EjercicioFicha | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCargando(true);
    catalogoApi.ficha(ejercicioId)
      .then(f => { setFicha(f); setError(null); })
      .catch(e => setError(e instanceof Error ? e.message : 'No se pudo cargar el ejercicio.'))
      .finally(() => setCargando(false));
  }, [ejercicioId]);

  return (
    <div className="velo" role="dialog" aria-modal="true" onClick={onCerrar}>
      <div className="hoja stack" style={{ gap: 16 }} onClick={e => e.stopPropagation()}>
        <div className="fila" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: 18 }}>Detalles del ejercicio</h2>
          <button className="btn btn-texto" onClick={onCerrar} style={{ fontSize: 18, padding: '4px 8px' }}>✕</button>
        </div>

        {cargando && <p className="muted" style={{ textAlign: 'center', padding: 20 }}>Cargando detalles…</p>}
        {error && <Aviso>{error}</Aviso>}

        {ficha && (
          <div className="stack" style={{ gap: 14 }}>
            <div className="stack" style={{ gap: 4 }}>
              <h3 style={{ fontSize: 20, color: 'var(--ink)' }}>{ficha.nombre}</h3>
              <div className="fila" style={{ gap: 8, flexWrap: 'wrap' }}>
                <span className="chip" style={{ fontSize: 12 }}>{CATEGORIA_TEXTO[ficha.categoria_equipo] ?? ficha.categoria_equipo}</span>
                <span className="chip" style={{ fontSize: 12 }}>{DIFICULTAD_TEXTO[ficha.dificultad] ?? ficha.dificultad}</span>
                {ficha.multiarticular && <span className="chip" style={{ fontSize: 12 }}>Multiarticular</span>}
              </div>
            </div>

            {/* MAPA ANATÓMICO CON ZONAS MARCADAS */}
            <section className="stack" style={{ gap: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--muted)' }}>Área muscular trabajada:</span>
              <MapaMuscular
                musculoPrincipal={ficha.musculo_principal}
                musculosSecundarios={ficha.musculos_secundarios}
                ancho={240}
                alto={220}
              />
            </section>

            {/* MÁQUINAS O EQUIPOS */}
            {ficha.maquinas.length > 0 && (
              <section className="stack" style={{ gap: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--muted)' }}>Máquinas / Equipos compatibles:</span>
                <div className="fila" style={{ gap: 6, flexWrap: 'wrap' }}>
                  {ficha.maquinas.map(m => (
                    <span key={m.codigo} className="chip" style={{ fontWeight: 600, background: 'var(--primary-tint)', color: 'var(--primary-dark)' }}>
                      {m.nombre}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {/* INSTRUCCIONES DE EJECUCIÓN */}
            <section className="stack" style={{ gap: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--muted)' }}>Instrucciones y técnica:</span>
              <p style={{ fontSize: 14, lineHeight: 1.5, background: 'var(--bg)', padding: 12, borderRadius: 10 }}>
                {ficha.instrucciones}
              </p>
            </section>

            {/* CONTRAINDICACIONES Y PRECAUCIONES */}
            {ficha.contraindicaciones.length > 0 && (
              <section className="stack" style={{ gap: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--muted)' }}>Precauciones en lesiones:</span>
                <div className="stack" style={{ gap: 6 }}>
                  {ficha.contraindicaciones.map(c => (
                    <div key={c.zona} className="fila" style={{
                      gap: 8, fontSize: 13, padding: '8px 10px', borderRadius: 8,
                      background: c.nivel === 'evitar' ? 'var(--danger-tint)' : 'var(--warning-tint)',
                      color: c.nivel === 'evitar' ? 'var(--danger)' : 'var(--warning)',
                    }}>
                      <IconAlertTriangle width={16} height={16} style={{ flexShrink: 0 }} />
                      <span>
                        <b>{c.zona_nombre}:</b> {c.nivel === 'evitar' ? 'Evitar si hay dolor o lesión activa' : 'Usar con precaución y carga moderada'}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            <button className="btn btn-claro" onClick={onCerrar} style={{ marginTop: 8 }}>
              Cerrar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
