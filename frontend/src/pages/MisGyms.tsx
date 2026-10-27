/** PG-06: los gyms donde entreno (y otros lugares, como mi casa). Máximo 5. Primero el último usado. */
import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { IconChevronRight, IconDumbbell, IconPlus, IconSearch } from '../components/Icons';
import { Aviso, Campo, Insignia } from '../components/UI';
import { gymsApi } from '../lib/endpoints';
import type { GymsRespuesta } from '../lib/tipos';

export default function MisGyms() {
  const nav = useNavigate();
  const [datos, setDatos] = useState<GymsRespuesta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [nuevo, setNuevo] = useState({ nombre: '', ubicacion: '' });
  const [enviando, setEnviando] = useState(false);

  const cargar = useCallback(() => gymsApi.listar().then(d => { setDatos(d); if (!d.gyms.length) setAbierto(true); }).catch(e => setError(e.message)), []);
  useEffect(() => { void cargar(); }, [cargar]);

  async function crear(ev: FormEvent) {
    ev.preventDefault();
    setError(null); setEnviando(true);
    try {
      const g = await gymsApi.crear({ nombre: nuevo.nombre.trim(), ubicacion: nuevo.ubicacion.trim() || undefined });
      nav(`/gyms/${g.id}`); // un gym nuevo arranca vacío: su pantalla guía a tomar las primeras fotos
    } catch (e) { setError(e instanceof Error ? e.message : 'No se pudo crear el gym.'); setEnviando(false); }
  }

  const lleno = !!datos && datos.gyms.length >= datos.maximo;

  return (
    <div className="pantalla stack" style={{ gap: 16 }}>
      <header className="stack" style={{ gap: 6, paddingTop: 8 }}>
        <h1 style={{ fontSize: 24 }}>Mis gyms</h1>
        <p className="muted" style={{ fontSize: 14 }}>Registra dónde entrenas. Tu plan se adapta a las máquinas de cada lugar.</p>
      </header>
      {error && <Aviso>{error}</Aviso>}

      {!!datos?.gyms.length && (
        <div className="grilla-tarjetas" style={{ gap: 16 }}>
          {datos.gyms.map(g => (
            <Link key={g.id} to={`/gyms/${g.id}`} className="card fila" style={{ textDecoration: 'none', color: 'inherit', gap: 12 }}>
              <span style={{ width: 44, height: 44, borderRadius: 12, background: 'var(--primary-tint)', display: 'grid', placeItems: 'center', flexShrink: 0 }}>
                <IconDumbbell style={{ color: 'var(--primary-dark)' }} />
              </span>
              <span className="stack" style={{ gap: 3, flex: 1, minWidth: 0 }}>
                <span className="fila" style={{ gap: 8, flexWrap: 'wrap' }}>
                  <b style={{ fontSize: 16 }}>{g.nombre}</b>
                  {g.es_ultimo_usado && <Insignia tono="ok">Último usado</Insignia>}
                </span>
                {g.ubicacion && <span className="muted" style={{ fontSize: 13 }}>{g.ubicacion}</span>}
                <span className="muted" style={{ fontSize: 13 }}>
                  {g.maquinas === 0 && g.implementos === 0 ? 'Vacío: agrega sus máquinas' : `${g.maquinas} máquinas · ${g.implementos} implementos`}
                </span>
              </span>
              <IconChevronRight style={{ color: 'var(--muted-2)' }} />
            </Link>
          ))}
        </div>
      )}

      {lleno && <Aviso tipo="info">Llegaste al máximo de {datos!.maximo} gyms. Elimina uno para agregar otro.</Aviso>}

      {!lleno && datos && !abierto && (
        <button className="btn btn-auto" onClick={() => setAbierto(true)}><IconPlus width={18} height={18} /> Agregar gym</button>
      )}
      {!lleno && abierto && (
        <form className="card stack form-angosto" onSubmit={crear}>
          <h2 style={{ fontSize: 17 }}>{datos?.gyms.length ? 'Nuevo gym' : 'Registra tu primer gym'}</h2>
          <Campo etiqueta="Nombre" placeholder="Ej. Gym Centro, Mi casa" maxLength={60} required autoFocus
            value={nuevo.nombre} onChange={e => setNuevo(p => ({ ...p, nombre: e.target.value }))} />
          <Campo etiqueta="Ubicación (opcional)" placeholder="Ej. Av. Busch y Beni" maxLength={120}
            value={nuevo.ubicacion} onChange={e => setNuevo(p => ({ ...p, ubicacion: e.target.value }))} />
          <button className="btn" disabled={!nuevo.nombre.trim() || enviando}>{enviando ? 'Guardando…' : 'Crear gym'}</button>
          {!!datos?.gyms.length && <button type="button" className="btn btn-texto" style={{ alignSelf: 'center' }} onClick={() => setAbierto(false)}>Cancelar</button>}
        </form>
      )}

      <Link to="/ejercicios" className="card fila" style={{ textDecoration: 'none', color: 'inherit', gap: 12, border: '1px dashed var(--border)' }}>
        <span style={{ width: 44, height: 44, borderRadius: 12, background: 'var(--primary-tint)', display: 'grid', placeItems: 'center', flexShrink: 0 }}>
          <IconSearch style={{ color: 'var(--primary-dark)' }} />
        </span>
        <span className="stack" style={{ gap: 2, flex: 1 }}>
          <b style={{ fontSize: 15 }}>Explorar catálogo y ejercicios</b>
          <span className="muted" style={{ fontSize: 13 }}>Revisa las 46 máquinas (péndulo, poleas) y su mapa muscular humano</span>
        </span>
        <IconChevronRight style={{ color: 'var(--muted-2)' }} />
      </Link>
    </div>
  );
}
