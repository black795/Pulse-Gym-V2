/**
 * Armar mi gym con fotos (PG-07, PG-08, PG-09).
 * Modo recorrido: el usuario toma (o elige) varias fotos seguidas; cada una se reduce, se sube con su barra de
 * progreso (se puede cancelar), la IA la reconoce y queda lista para revisar. Sin señal, las fotos esperan
 * guardadas en el celular y se suben solas al volver la conexión.
 */
import { useCallback, useEffect, useRef, useState, type ChangeEvent } from 'react';
import { Link, useParams } from 'react-router';
import Camara from '../components/Camara';
import RevisarFoto from '../components/RevisarFoto';
import { IconAlertTriangle, IconCamera, IconCheck, IconImage, IconShield } from '../components/Icons';
import { Aviso, Volver } from '../components/UI';
import { colaFotos } from '../lib/colaFotos';
import { fotosApi, gymsApi } from '../lib/endpoints';
import { ApiError } from '../lib/http';
import { reducirImagen, validarArchivo } from '../lib/imagen';
import type { Foto, GymDetalle, Reconocimiento } from '../lib/tipos';

type Estado = 'en_espera' | 'pendiente' | 'subiendo' | 'reconociendo' | 'revisar' | 'error' | 'listo';
interface Item {
  clave: string; vista: string; blob: Blob; estado: Estado; progreso: number;
  foto?: Foto; rec?: Reconocimiento; error?: string; mensaje?: string; cancelar?: () => void;
  /** PG-49: se llegó al límite diario de la IA; reintentar no sirve, solo elegir a mano. */
  sinReintento?: boolean;
}

const nuevaClave = () => (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`);

export default function AgregarMaquinas() {
  const gymId = Number(useParams().id);
  const [gym, setGym] = useState<GymDetalle | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [camara, setCamara] = useState(false);
  const [tomadas, setTomadas] = useState(0); // fotos de esta pasada con la cámara (modo recorrido)
  const [revisando, setRevisando] = useState<{ clave: string; manual: boolean } | null>(null);
  const [enLinea, setEnLinea] = useState(navigator.onLine);
  const [aviso, setAviso] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const galeria = useRef<HTMLInputElement>(null);
  const camaraSistema = useRef<HTMLInputElement>(null);
  const procesando = useRef(false);

  const actualizar = useCallback((clave: string, cambios: Partial<Item>) =>
    setItems(lista => lista.map(i => (i.clave === clave ? { ...i, ...cambios } : i))), []);

  useEffect(() => { gymsApi.ver(gymId).then(setGym).catch(e => setError(e.message)); }, [gymId]);

  // Fotos que quedaron en espera (sin señal o porque se cerró la app) se retoman al abrir la pantalla.
  useEffect(() => {
    let activo = true;
    colaFotos.delGym(gymId).then(pendientes => {
      if (!activo || !pendientes.length) return;
      setItems(lista => [
        ...pendientes.filter(p => !lista.some(i => i.clave === p.clave)).map<Item>(p => ({
          clave: p.clave, blob: p.foto, vista: URL.createObjectURL(p.foto), progreso: 0,
          estado: navigator.onLine ? 'pendiente' : 'en_espera',
        })),
        ...lista,
      ]);
    });
    return () => { activo = false; };
  }, [gymId]);

  useEffect(() => {
    const conectado = () => { setEnLinea(true); setItems(l => l.map(i => (i.estado === 'en_espera' ? { ...i, estado: 'pendiente' } : i))); };
    const desconectado = () => setEnLinea(false);
    window.addEventListener('online', conectado);
    window.addEventListener('offline', desconectado);
    return () => { window.removeEventListener('online', conectado); window.removeEventListener('offline', desconectado); };
  }, []);

  // Libera las vistas previas al salir.
  const itemsRef = useRef(items);
  itemsRef.current = items;
  useEffect(() => () => itemsRef.current.forEach(i => URL.revokeObjectURL(i.vista)), []);

  const reconocer = useCallback(async (clave: string, foto: Foto) => {
    actualizar(clave, { estado: 'reconociendo', error: undefined, sinReintento: false });
    try {
      const rec = await fotosApi.reconocer(foto.id);
      actualizar(clave, { estado: 'revisar', rec });
    } catch (e) {
      const msg = e instanceof ApiError && e.codigo === 'tiempo_agotado'
        ? 'La IA tardó demasiado. Reintenta o elige la máquina a mano.'
        : e instanceof Error ? e.message : 'La IA no respondió.';
      actualizar(clave, { estado: 'error', error: msg, sinReintento: e instanceof ApiError && e.codigo === 'limite_ia' });
    }
  }, [actualizar]);

  const procesar = useCallback(async (item: Item) => {
    procesando.current = true;
    try {
      if (item.foto) { await reconocer(item.clave, item.foto); return; }
      const subida = gymsApi.subirFoto(gymId, item.blob, pct => actualizar(item.clave, { progreso: pct }));
      actualizar(item.clave, { estado: 'subiendo', progreso: 0, cancelar: subida.cancelar });
      let foto: Foto;
      try {
        foto = await subida.promesa;
      } catch (e) {
        if (e instanceof ApiError && e.codigo === 'cancelada') {
          void colaFotos.quitar(item.clave);
          URL.revokeObjectURL(item.vista);
          setItems(l => l.filter(i => i.clave !== item.clave));
        } else if (e instanceof ApiError && e.codigo === 'sin_conexion') {
          actualizar(item.clave, { estado: 'en_espera', cancelar: undefined }); // sigue guardada en el celular
          if (navigator.onLine) setTimeout(() => actualizar(item.clave, { estado: 'pendiente' }), 5000); // el servidor no respondió: reintenta
        } else {
          void colaFotos.quitar(item.clave); // el servidor la rechazó: no sirve reintentarla
          actualizar(item.clave, { estado: 'error', error: e instanceof Error ? e.message : 'No se pudo subir.', cancelar: undefined });
        }
        return;
      }
      void colaFotos.quitar(item.clave);
      actualizar(item.clave, { foto, cancelar: undefined, progreso: 100 });
      await reconocer(item.clave, foto);
    } finally {
      procesando.current = false;
      setItems(l => [...l]); // despierta la cola para la siguiente foto
    }
  }, [actualizar, gymId, reconocer]);

  // Una foto a la vez (la capa gratuita de la IA admite pocas consultas por minuto).
  useEffect(() => {
    if (procesando.current || items.some(i => i.estado === 'subiendo' || i.estado === 'reconociendo')) return;
    const siguiente = items.find(i => i.estado === 'pendiente');
    if (siguiente) void procesar(siguiente);
  }, [items, procesar]);

  // Al cerrar la cámara, abre sola la siguiente foto lista para revisar (salvo las que el usuario cerró a propósito).
  const cerradas = useRef(new Set<string>());
  useEffect(() => {
    if (camara || revisando) return;
    const lista = items.find(i => i.estado === 'revisar' && !cerradas.current.has(i.clave));
    if (lista) setRevisando({ clave: lista.clave, manual: false });
  }, [items, camara, revisando]);

  async function agregar(fotos: Blob[]) {
    const nuevos: Item[] = [];
    for (const original of fotos) {
      const blob = await reducirImagen(original);
      const clave = nuevaClave();
      await colaFotos.guardar({ clave, gymId, foto: blob, creada: Date.now() });
      nuevos.push({ clave, blob, vista: URL.createObjectURL(blob), progreso: 0, estado: navigator.onLine ? 'pendiente' : 'en_espera' });
    }
    setItems(l => [...l, ...nuevos]);
  }

  function elegirArchivos(e: ChangeEvent<HTMLInputElement>) {
    const archivos = Array.from(e.target.files ?? []);
    e.target.value = ''; // permite volver a elegir la misma foto
    const malos = archivos.map(validarArchivo).filter(Boolean) as string[];
    setError(malos.length ? malos.join(' ') : null);
    void agregar(archivos.filter(f => !validarArchivo(f)));
    setCamara(false);
  }

  const abierto = revisando ? items.find(i => i.clave === revisando.clave) : undefined;
  const listas = items.filter(i => i.estado === 'listo').length;
  const enEspera = items.filter(i => i.estado === 'en_espera').length;

  return (
    <div className="pantalla stack" style={{ gap: 16 }}>
      <Volver a={`/gyms/${gymId}`} texto={gym ? gym.nombre : 'Mi gym'} />
      <header className="stack" style={{ gap: 6 }}>
        <h1 style={{ fontSize: 24 }}>Agregar máquinas</h1>
        <p className="muted" style={{ fontSize: 14 }}>Fotografía cada máquina. La IA la reconoce y tú confirmas.</p>
      </header>

      <div className="card fila" style={{ alignItems: 'flex-start', gap: 12 }}>
        <IconShield width={22} height={22} style={{ color: 'var(--primary-dark)', flexShrink: 0, marginTop: 2 }} />
        <p style={{ fontSize: 13.5, lineHeight: 1.45 }}>
          <b>Encuadra solo la máquina, completa y sin otras personas.</b> Tus fotos son privadas: solo las usamos para reconocer la máquina.
        </p>
      </div>

      {!enLinea && <Aviso tipo="info">Sin conexión. Tus fotos quedan guardadas en el celular y se suben solas cuando vuelva la señal.</Aviso>}
      {error && <Aviso>{error}</Aviso>}
      {aviso && <Aviso tipo="ok">{aviso}</Aviso>}

      <div className="grid-2 acciones">
        <button className="btn btn-neon" style={{ minHeight: 64 }} onClick={() => { setTomadas(0); setCamara(true); }}><IconCamera width={20} height={20} /> Tomar fotos</button>
        <button className="btn btn-claro" style={{ minHeight: 64 }} onClick={() => galeria.current?.click()}><IconImage width={20} height={20} /> Galería</button>
      </div>
      <input ref={galeria} type="file" accept="image/jpeg,image/png,image/heic,image/heif,.heic,.heif" multiple hidden onChange={elegirArchivos} />
      <input ref={camaraSistema} type="file" accept="image/*" capture="environment" hidden onChange={elegirArchivos} />

      {items.length > 0 && (
        <section className="stack" style={{ gap: 10 }}>
          <div className="fila" style={{ justifyContent: 'space-between' }}>
            <h2 style={{ fontSize: 16 }}>Tus fotos</h2>
            <span className="muted" style={{ fontSize: 13 }}>{listas} de {items.length} listas{enEspera ? ` · ${enEspera} en espera` : ''}</span>
          </div>
          <div className="grilla-tarjetas">
            {items.map(i => (
              <FilaFoto key={i.clave} item={i}
                onRevisar={() => setRevisando({ clave: i.clave, manual: false })}
                onManual={() => setRevisando({ clave: i.clave, manual: true })}
                onReintentar={() => (i.foto ? void reconocer(i.clave, i.foto) : actualizar(i.clave, { estado: 'pendiente' }))}
                onQuitar={() => { void colaFotos.quitar(i.clave); URL.revokeObjectURL(i.vista); setItems(l => l.filter(x => x.clave !== i.clave)); }} />
            ))}
          </div>
        </section>
      )}

      {items.length === 0 && (
        <p className="muted" style={{ textAlign: 'center', fontSize: 14, padding: '8px 12px' }}>
          Consejo: recorre el gym y toma una foto por máquina, sin cerrar la cámara. Al terminar, revisas todas.
        </p>
      )}

      {listas > 0 && <Link to={`/gyms/${gymId}`} className="btn btn-claro btn-auto">Ver mi inventario</Link>}

      {camara && (
        <Camara tomadas={tomadas}
          onFoto={b => { setTomadas(n => n + 1); void agregar([b]); }}
          onGaleria={() => galeria.current?.click()}
          onCamaraSistema={() => camaraSistema.current?.click()}
          onCerrar={() => setCamara(false)} />
      )}

      {abierto?.foto && (
        <RevisarFoto key={abierto.clave} fotoId={abierto.foto.id} vista={abierto.vista} rec={revisando?.manual ? null : abierto.rec ?? null}
          onCerrar={() => { cerradas.current.add(abierto.clave); setRevisando(null); }}
          onHecho={m => { actualizar(abierto.clave, { estado: 'listo', mensaje: m }); setAviso(m); setRevisando(null); }}
          onDescartada={() => {
            URL.revokeObjectURL(abierto.vista);
            setItems(l => l.filter(x => x.clave !== abierto.clave));
            setRevisando(null);
          }} />
      )}
    </div>
  );
}

function FilaFoto({ item: i, onRevisar, onManual, onReintentar, onQuitar }: {
  item: Item; onRevisar: () => void; onManual: () => void; onReintentar: () => void; onQuitar: () => void;
}) {
  const texto: Record<Estado, string> = {
    en_espera: 'En espera de señal…', pendiente: 'En cola…', subiendo: `Subiendo… ${i.progreso}%`,
    reconociendo: 'La IA está reconociendo la máquina…', revisar: i.rec?.confianza_alta ? `¿Es ${i.rec.sugerencias[0]?.maquina.nombre}?` : 'Lista para revisar',
    error: i.error ?? 'Ocurrió un error.', listo: i.mensaje ?? 'Agregada',
  };
  return (
    <div className="card fila" style={{ padding: 10, gap: 12, alignItems: 'center' }}>
      <img className="miniatura" src={i.vista} alt="" />
      <div className="stack" style={{ gap: 6, flex: 1, minWidth: 0 }}>
        <span style={{ fontSize: 13.5, fontWeight: 600, color: i.estado === 'error' ? 'var(--danger)' : undefined }}>
          {i.estado === 'listo' && <IconCheck width={15} height={15} style={{ color: 'var(--primary)', verticalAlign: -2, marginRight: 4 }} />}
          {i.estado === 'error' && <IconAlertTriangle width={15} height={15} style={{ verticalAlign: -2, marginRight: 4 }} />}
          {texto[i.estado]}
        </span>
        {i.estado === 'subiendo' && <div className="barra-subida" aria-hidden="true"><span style={{ width: `${i.progreso}%` }} /></div>}
        {i.estado === 'reconociendo' && <div className="barra-subida pulse-latido" aria-hidden="true"><span style={{ width: '100%', opacity: .5 }} /></div>}
        <div className="fila" style={{ gap: 4, flexWrap: 'wrap' }}>
          {i.estado === 'subiendo' && i.cancelar && <button className="btn btn-texto" onClick={i.cancelar}>Cancelar</button>}
          {i.estado === 'revisar' && <button className="btn btn-texto" onClick={onRevisar}>Revisar</button>}
          {i.estado === 'error' && !i.sinReintento && <button className="btn btn-texto" onClick={onReintentar}>Reintentar</button>}
          {i.estado === 'error' && i.foto && <button className="btn btn-texto" onClick={onManual}>Elegir a mano</button>}
          {(i.estado === 'error' && !i.foto) || i.estado === 'en_espera' ? <button className="btn btn-texto" style={{ color: 'var(--danger)' }} onClick={onQuitar}>Quitar</button> : null}
        </div>
      </div>
    </div>
  );
}
