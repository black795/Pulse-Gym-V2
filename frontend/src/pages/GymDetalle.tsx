/**
 * Un gym: inventario de máquinas (PG-12, PG-13), implementos (PG-14), renombrar y eliminar (PG-06).
 * Abrir un gym lo marca como "el último usado".
 */
import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { IconCamera, IconEdit, IconSearch, IconTrash } from '../components/Icons';
import ModalAgregarCatalogo from '../components/ModalAgregarCatalogo';
import { Aviso, Campo, Volver, aNumero } from '../components/UI';
import { colaFotos } from '../lib/colaFotos';
import { gymsApi } from '../lib/endpoints';
import { urlApi } from '../lib/http';
import type { EstadoMaquina, GymDetalle as Gym, GymMaquina, MaquinaCatalogo } from '../lib/tipos';

const ESTADOS: { valor: EstadoMaquina; texto: string }[] = [
  { valor: 'disponible', texto: 'Disponible' }, { valor: 'malograda', texto: 'Malograda' }, { valor: 'retirada', texto: 'Ya no está' },
];

export default function GymDetalle() {
  const id = Number(useParams().id);
  const nav = useNavigate();
  const [gym, setGym] = useState<Gym | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editando, setEditando] = useState(false);
  const [form, setForm] = useState({ nombre: '', ubicacion: '' });
  const [confirmaBorrar, setConfirmaBorrar] = useState(false);
  const [enEspera, setEnEspera] = useState(0);
  const [kg, setKg] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const [modalCatalogo, setModalCatalogo] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargar = useCallback(() => gymsApi.ver(id).then(g => { setGym(g); setKg(g.mancuernas_max_kg?.toString() ?? ''); }).catch(e => setError(e.message)), [id]);
  useEffect(() => {
    void gymsApi.usar(id).catch(() => {}); // PG-06: se recuerda el último gym usado
    void cargar();
    colaFotos.delGym(id).then(p => setEnEspera(p.length));
  }, [id, cargar]);

  async function agregarManual(maquina: MaquinaCatalogo) {
    setError(null);
    const gm = await gymsApi.agregarMaquina(id, maquina.codigo);
    setGym(g => g && {
      ...g,
      inventario: [gm, ...g.inventario.filter(x => x.id !== gm.id)],
      maquinas: g.maquinas + (g.inventario.some(x => x.id === gm.id && x.estado !== 'retirada') ? 0 : 1),
    });
    setAviso(`«${maquina.nombre}» agregada a tu gym.`);
  }

  async function guardarDatos(ev: FormEvent) {
    ev.preventDefault();
    setError(null); setOcupado(true);
    try {
      await gymsApi.cambiar(id, { nombre: form.nombre.trim(), ubicacion: form.ubicacion.trim() || null });
      setEditando(false); await cargar();
    } catch (e) { setError(e instanceof Error ? e.message : 'No se pudo guardar.'); }
    finally { setOcupado(false); }
  }

  async function eliminar() {
    setOcupado(true);
    try { await gymsApi.eliminar(id); nav('/gyms', { replace: true }); }
    catch (e) { setError(e instanceof Error ? e.message : 'No se pudo eliminar.'); setOcupado(false); }
  }

  async function guardarImplementos(implementos: string[], maxKg: number | null) {
    setError(null);
    try {
      const g = await gymsApi.implementos(id, { implementos, mancuernas_max_kg: maxKg });
      setGym(g); setKg(g.mancuernas_max_kg?.toString() ?? '');
    } catch (e) { setError(e instanceof Error ? e.message : 'No se pudieron guardar los implementos.'); }
  }

  const reemplazar = (gm: GymMaquina) => setGym(g => g && { ...g, inventario: g.inventario.map(x => (x.id === gm.id ? gm : x)) });

  if (!gym) return <div className="pantalla stack"><Volver a="/gyms" texto="Mis gyms" />{error ? <Aviso>{error}</Aviso> : <p className="muted">Cargando…</p>}</div>;

  const marcados = gym.lista_implementos.filter(i => i.marcado).map(i => i.codigo);
  const activas = gym.inventario.filter(m => m.estado !== 'retirada');
  const retiradas = gym.inventario.filter(m => m.estado === 'retirada');
  const vacio = gym.inventario.length === 0 && marcados.length === 0;

  return (
    <div className="pantalla stack" style={{ gap: 16 }}>
      <Volver a="/gyms" texto="Mis gyms" />

      {!editando ? (
        <header className="fila" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div className="stack" style={{ gap: 4 }}>
            <h1 style={{ fontSize: 24 }}>{gym.nombre}</h1>
            {gym.ubicacion && <p className="muted" style={{ fontSize: 14 }}>{gym.ubicacion}</p>}
          </div>
          <button className="btn btn-texto" aria-label="Editar nombre y ubicación"
            onClick={() => { setForm({ nombre: gym.nombre, ubicacion: gym.ubicacion ?? '' }); setEditando(true); }}>
            <IconEdit width={18} height={18} /> Editar
          </button>
        </header>
      ) : (
        <form className="card stack" onSubmit={guardarDatos}>
          <Campo etiqueta="Nombre" maxLength={60} required value={form.nombre} onChange={e => setForm(p => ({ ...p, nombre: e.target.value }))} />
          <Campo etiqueta="Ubicación (opcional)" maxLength={120} value={form.ubicacion} onChange={e => setForm(p => ({ ...p, ubicacion: e.target.value }))} />
          <button className="btn" disabled={!form.nombre.trim() || ocupado}>Guardar</button>
          <button type="button" className="btn btn-texto" style={{ alignSelf: 'center' }} onClick={() => setEditando(false)}>Cancelar</button>
        </form>
      )}

      {error && <Aviso>{error}</Aviso>}
      {aviso && <Aviso tipo="ok">{aviso}</Aviso>}
      {enEspera > 0 && (
        <Link to={`/gyms/${id}/agregar`} className="aviso aviso-info" style={{ textDecoration: 'none' }}>
          Tienes {enEspera} {enEspera === 1 ? 'foto' : 'fotos'} sin subir. Toca aquí para subirlas.
        </Link>
      )}

      {vacio ? (
        <div className="card stack" style={{ gap: 10, borderColor: 'var(--primary)' }}>
          <h2 style={{ fontSize: 17 }}>Tu gym está vacío</h2>
          <p className="muted" style={{ fontSize: 14 }}>
            Toma fotos de tus máquinas para que la IA las reconozca, o agrégalas directamente desde el catálogo oficial.
          </p>
          <div className="grid-2">
            <Link to={`/gyms/${id}/agregar`} className="btn btn-neon"><IconCamera width={20} height={20} /> Tomar fotos</Link>
            <button type="button" className="btn btn-claro" onClick={() => setModalCatalogo(true)}><IconSearch width={18} height={18} /> Desde catálogo</button>
          </div>
        </div>
      ) : (
        <div className="grid-2">
          <Link to={`/gyms/${id}/agregar`} className="btn btn-neon"><IconCamera width={20} height={20} /> Tomar fotos</Link>
          <button type="button" className="btn btn-claro" onClick={() => setModalCatalogo(true)}><IconSearch width={18} height={18} /> Desde catálogo</button>
        </div>
      )}

      {activas.length > 0 && (
        <section className="stack" style={{ gap: 10 }}>
          <h2 style={{ fontSize: 16 }}>Máquinas ({activas.length})</h2>
          {activas.map(m => <FilaMaquina key={m.id} gymId={id} m={m} onCambio={reemplazar} onQuitada={cargar} onError={setError} />)}
        </section>
      )}

      {retiradas.length > 0 && (
        <details className="card">
          <summary style={{ cursor: 'pointer', fontWeight: 700, minHeight: 28 }}>Ya no están en el gym ({retiradas.length})</summary>
          <div className="stack" style={{ gap: 10, marginTop: 12 }}>
            {retiradas.map(m => <FilaMaquina key={m.id} gymId={id} m={m} onCambio={reemplazar} onQuitada={cargar} onError={setError} />)}
          </div>
        </details>
      )}

      <section className="card stack" style={{ gap: 12 }}>
        <h2 style={{ fontSize: 16 }}>Implementos</h2>
        <p className="muted" style={{ fontSize: 13.5 }}>Marca lo que hay, sin fotografiarlo. Los ejercicios con tu peso corporal siempre están disponibles.</p>
        <div className="chips">
          {gym.lista_implementos.map(i => (
            <button key={i.codigo} type="button" className="chip" aria-pressed={i.marcado}
              onClick={() => guardarImplementos(i.marcado ? marcados.filter(c => c !== i.codigo) : [...marcados, i.codigo], aNumero(kg) ?? null)}>
              {i.marcado && '✓ '}{i.nombre}
            </button>
          ))}
        </div>
        {marcados.includes('mancuernas') && (
          <Campo etiqueta="Peso máximo de las mancuernas (opcional)" ayuda="En kg, por mancuerna. Ej. 30" inputMode="decimal"
            value={kg} onChange={e => setKg(e.target.value)}
            onBlur={() => { if ((aNumero(kg) ?? null) !== gym.mancuernas_max_kg) void guardarImplementos(marcados, aNumero(kg) ?? null); }} />
        )}
      </section>

      <section className="card stack" style={{ gap: 10 }}>
        <h2 style={{ fontSize: 15, color: 'var(--danger)' }}>Eliminar este gym</h2>
        <p className="muted" style={{ fontSize: 13.5 }}>Se borran sus máquinas y sus fotos. Tu historial de entrenamientos se conserva.</p>
        {!confirmaBorrar
          ? <button className="btn btn-claro" onClick={() => setConfirmaBorrar(true)}><IconTrash width={18} height={18} /> Eliminar gym</button>
          : <>
              <button className="btn btn-peligro" disabled={ocupado} onClick={eliminar}>Sí, eliminar «{gym.nombre}»</button>
              <button className="btn btn-claro" onClick={() => setConfirmaBorrar(false)}>No, volver</button>
            </>}
      </section>

      {modalCatalogo && (
        <ModalAgregarCatalogo
          gymId={id}
          codigosExistentes={activas.map(a => a.maquina.codigo)}
          onAgregar={agregarManual}
          onCerrar={() => setModalCatalogo(false)}
        />
      )}
    </div>
  );
}

function FilaMaquina({ gymId, m, onCambio, onQuitada, onError }: {
  gymId: number; m: GymMaquina; onCambio: (m: GymMaquina) => void; onQuitada: () => void; onError: (e: string) => void;
}) {
  const [confirmar, setConfirmar] = useState<'retirada' | 'quitar' | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function cambiar(estado: EstadoMaquina) {
    if (estado === m.estado) return;
    if (estado === 'retirada' && confirmar !== 'retirada') { setConfirmar('retirada'); return; } // "retirada" pide confirmación
    setOcupado(true);
    try { onCambio(await gymsApi.estadoMaquina(gymId, m.id, estado)); setConfirmar(null); }
    catch (e) { onError(e instanceof Error ? e.message : 'No se pudo cambiar el estado.'); }
    finally { setOcupado(false); }
  }

  async function quitar() {
    setOcupado(true);
    try { await gymsApi.quitarMaquina(gymId, m.id); onQuitada(); }
    catch (e) { onError(e instanceof Error ? e.message : 'No se pudo quitar.'); setOcupado(false); }
  }

  const foto = m.foto_url ? urlApi(m.foto_url) : m.maquina.foto_ref;
  return (
    <div className="card stack" style={{ gap: 10, padding: 12 }}>
      <div className="fila" style={{ gap: 12 }}>
        {foto ? <img className="miniatura" src={foto} alt="" loading="lazy" /> : <span className="miniatura" />}
        <div className="stack" style={{ gap: 2, flex: 1, minWidth: 0 }}>
          <b style={{ fontSize: 15 }}>{m.maquina.nombre}</b>
          <span className="muted" style={{ fontSize: 13 }}>{m.maquina.musculo_principal ?? 'Varios músculos'}</span>
        </div>
        <button className="btn btn-texto" aria-label={`Quitar ${m.maquina.nombre}`} onClick={() => setConfirmar('quitar')}>
          <IconTrash width={18} height={18} style={{ color: 'var(--muted)' }} />
        </button>
      </div>
      <div className="segmento" role="group" aria-label="Estado de la máquina">
        {ESTADOS.map(e => (
          <button key={e.valor} type="button" data-estado={e.valor} aria-pressed={m.estado === e.valor} disabled={ocupado} onClick={() => cambiar(e.valor)}>{e.texto}</button>
        ))}
      </div>
      {confirmar === 'retirada' && (
        <div className="stack" style={{ gap: 8 }}>
          <p style={{ fontSize: 13.5 }}>¿La sacaron del gym? No se usará en tus rutinas. Si vuelve, la puedes reactivar.</p>
          <div className="grid-2">
            <button className="btn btn-peligro" disabled={ocupado} onClick={() => cambiar('retirada')}>Sí, ya no está</button>
            <button className="btn btn-claro" onClick={() => setConfirmar(null)}>Cancelar</button>
          </div>
        </div>
      )}
      {confirmar === 'quitar' && (
        <div className="stack" style={{ gap: 8 }}>
          <p style={{ fontSize: 13.5 }}>¿La agregaste por error? Se quita del inventario y se borra su foto.</p>
          <div className="grid-2">
            <button className="btn btn-peligro" disabled={ocupado} onClick={quitar}>Sí, quitar</button>
            <button className="btn btn-claro" onClick={() => setConfirmar(null)}>Cancelar</button>
          </div>
        </div>
      )}
    </div>
  );
}
