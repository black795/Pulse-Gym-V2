/** Perfil y ajustes: editar datos (PG-02), registrar una medición nueva y controlar la privacidad (PG-05, PG-50). */
import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import Avatar from '../components/Avatar';
import { IconLogOut, IconTrash } from '../components/Icons';
import { Aviso, Campo, Insignia, Opciones, aNumero } from '../components/UI';
import { useAuth } from '../features/auth/AuthContext';
import { perfilApi } from '../lib/endpoints';
import { ApiError } from '../lib/http';
import type { Medicion, PerfilEnvio } from '../lib/tipos';
import { NIVELES, OBJETIVOS, SEXOS, nombreDe, usePerfil } from '../lib/usePerfil';

const fecha = (iso: string) => new Date(iso + 'T00:00:00').toLocaleDateString('es-BO', { day: 'numeric', month: 'short' });

export default function Perfil() {
  const nav = useNavigate();
  const { usuario, logout, refrescar } = useAuth();
  const { perfil, setPerfil, error: errorCarga, recargar } = usePerfil();
  const [mediciones, setMediciones] = useState<Medicion[]>([]);
  const [msg, setMsg] = useState<{ tipo: 'ok' | 'error'; texto: string } | null>(null);
  const [edit, setEdit] = useState({ edad: '', altura: '', sexo: '', objetivo: '', nivel: '', dias: '', minutos: '' });
  const [med, setMed] = useState({ peso: '', grasa: '', masa: '' });
  const [confirmaBorrar, setConfirmaBorrar] = useState(false);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => { perfilApi.mediciones().then(setMediciones).catch(() => {}); }, [perfil?.ultima_medicion]);
  useEffect(() => {
    if (!perfil) return;
    const t = (n: number | null) => (n == null ? '' : String(n));
    setEdit({ edad: t(perfil.edad), altura: t(perfil.altura_cm), sexo: perfil.sexo ?? '', objetivo: perfil.objetivo ?? '', nivel: perfil.nivel ?? '',
      dias: t(perfil.dias_por_semana), minutos: t(perfil.minutos_por_sesion) });
  }, [perfil]);

  async function guardar(datos: PerfilEnvio, exito: string, despues?: () => void) {
    setMsg(null); setOcupado(true);
    try {
      setPerfil(await perfilApi.guardar(datos)); setMsg({ tipo: 'ok', texto: exito }); despues?.();
    } catch (e) {
      if (e instanceof ApiError && e.codigo === 'consentimiento_requerido') nav('/consentimiento?volver=/perfil');
      else setMsg({ tipo: 'error', texto: e instanceof Error ? e.message : 'No se pudo guardar.' });
    } finally { setOcupado(false); }
  }

  const guardarDatos = (e: FormEvent) => {
    e.preventDefault();
    const d: PerfilEnvio = { edad: aNumero(edit.edad), altura_cm: aNumero(edit.altura), sexo: edit.sexo || undefined, objetivo: edit.objetivo || undefined,
      nivel: edit.nivel || undefined, dias_por_semana: aNumero(edit.dias), minutos_por_sesion: aNumero(edit.minutos) };
    return guardar(Object.fromEntries(Object.entries(d).filter(([, v]) => v !== undefined)) as PerfilEnvio, 'Datos guardados.');
  };
  const guardarMedicion = (e: FormEvent) => {
    e.preventDefault();
    const d: PerfilEnvio = { peso_kg: aNumero(med.peso), grasa_pct: aNumero(med.grasa), masa_muscular_kg: aNumero(med.masa) };
    return guardar(Object.fromEntries(Object.entries(d).filter(([, v]) => v !== undefined)) as PerfilEnvio, 'Medición guardada.', () => setMed({ peso: '', grasa: '', masa: '' }));
  };

  async function cambiarConsentimiento(acepta: boolean) {
    setMsg(null); setOcupado(true);
    try { await perfilApi.fijarConsentimiento(acepta); await Promise.all([refrescar(), recargar()]);
      setMsg({ tipo: 'ok', texto: acepta ? 'Gracias, ya podemos guardar tus datos de salud.' : 'Listo: borramos tus datos de salud (peso, medidas y lesiones).' }); }
    catch (e) { setMsg({ tipo: 'error', texto: e instanceof Error ? e.message : 'No se pudo cambiar.' }); }
    finally { setOcupado(false); }
  }

  async function borrarCuenta() {
    setOcupado(true);
    try { await perfilApi.eliminarCuenta(); logout(); nav('/login', { replace: true }); }
    catch (e) { setMsg({ tipo: 'error', texto: e instanceof Error ? e.message : 'No se pudo eliminar la cuenta.' }); setOcupado(false); }
  }

  if (!usuario) return null;
  const estado = perfil?.consentimiento.estado;
  const sensibleOk = estado === 'aceptado';

  return (
    <div className="pantalla stack" style={{ gap: 16 }}>
      <header className="fila" style={{ paddingTop: 8 }}>
        <Avatar name={usuario.nombre} size={56} />
        <div style={{ minWidth: 0 }}>
          <h1 style={{ fontSize: 20 }}>{usuario.nombre}</h1>
          <p className="muted" style={{ fontSize: 13.5, overflow: 'hidden', textOverflow: 'ellipsis' }}>{usuario.email}</p>
        </div>
      </header>
      {errorCarga && <Aviso>{errorCarga}</Aviso>}
      {msg && <Aviso tipo={msg.tipo}>{msg.texto}</Aviso>}

      <div className="columnas-escritorio">
        <div className="stack" style={{ gap: 16 }}>
          {perfil && (
            <div className="card" style={{ fontSize: 14 }}>
              <div className="grid-2">
                <div><span className="muted">Objetivo</span><br /><b>{nombreDe(OBJETIVOS, perfil.objetivo)}</b></div>
                <div><span className="muted">Nivel</span><br /><b>{perfil.nivel ? perfil.nivel[0].toUpperCase() + perfil.nivel.slice(1) : '—'}</b></div>
                <div style={{ marginTop: 8 }}><span className="muted">Peso</span><br /><b>{perfil.ultima_medicion?.peso_kg ? `${perfil.ultima_medicion.peso_kg} kg` : '—'}</b></div>
                <div style={{ marginTop: 8 }}><span className="muted">IMC</span><br /><b>{perfil.imc ?? '—'}</b> {perfil.imc_categoria && <span className="muted">({perfil.imc_categoria})</span>}</div>
              </div>
            </div>
          )}

          <form className="card stack" onSubmit={guardarDatos}>
            <h2 style={{ fontSize: 17 }}>Mis datos</h2>
            <div className="grid-2">
              <Campo etiqueta="Edad" inputMode="numeric" value={edit.edad} onChange={e => setEdit(p => ({ ...p, edad: e.target.value }))} />
              <Campo etiqueta="Altura (cm)" inputMode="decimal" value={edit.altura} onChange={e => setEdit(p => ({ ...p, altura: e.target.value }))} disabled={!sensibleOk} />
            </div>
            <div className="campo"><label>Sexo</label><Opciones columnas={3} valor={edit.sexo} onCambio={v => setEdit(p => ({ ...p, sexo: v }))} opciones={SEXOS} /></div>
            <div className="campo"><label>Objetivo</label><Opciones valor={edit.objetivo} onCambio={v => setEdit(p => ({ ...p, objetivo: v }))} opciones={OBJETIVOS} /></div>
            <div className="campo"><label>Nivel</label><Opciones valor={edit.nivel} onCambio={v => setEdit(p => ({ ...p, nivel: v }))} opciones={NIVELES} /></div>
            <div className="grid-2">
              <Campo etiqueta="Días por semana" inputMode="numeric" value={edit.dias} onChange={e => setEdit(p => ({ ...p, dias: e.target.value }))} />
              <Campo etiqueta="Minutos por sesión" inputMode="numeric" value={edit.minutos} onChange={e => setEdit(p => ({ ...p, minutos: e.target.value }))} />
            </div>
            {perfil?.plan_requiere_regenerar && <Aviso tipo="info">Cambiaste datos que afectan tu plan. <Link to="/plan">Revisa tu plan</Link> para actualizarlo.</Aviso>}
            <button className="btn" disabled={ocupado}>Guardar cambios</button>
          </form>
        </div>

        <div className="stack" style={{ gap: 16 }}>
          <form className="card stack" onSubmit={guardarMedicion}>
            <h2 style={{ fontSize: 17 }}>Nueva medición</h2>
            {sensibleOk ? (
              <>
                <p className="muted" style={{ fontSize: 13.5 }}>Guarda tu peso de hoy para ver tu progreso. Si ya registraste hoy, se actualiza.</p>
                <Campo etiqueta="Peso (kg)" inputMode="decimal" value={med.peso} onChange={e => setMed(p => ({ ...p, peso: e.target.value }))} />
                <div className="grid-2">
                  <Campo etiqueta="% de grasa" inputMode="decimal" value={med.grasa} onChange={e => setMed(p => ({ ...p, grasa: e.target.value }))} />
                  <Campo etiqueta="Masa muscular (kg)" inputMode="decimal" value={med.masa} onChange={e => setMed(p => ({ ...p, masa: e.target.value }))} />
                </div>
                <button className="btn" disabled={ocupado || (!med.peso && !med.grasa && !med.masa)}>Guardar medición</button>
              </>
            ) : <p className="muted" style={{ fontSize: 13.5 }}>Para guardar mediciones necesitamos tu permiso (más abajo, en Privacidad).</p>}
            {mediciones.length > 0 && (
              <ul style={{ listStyle: 'none', margin: 0, padding: 0, fontSize: 14 }}>
                {[...mediciones].reverse().slice(0, 6).map(m => (
                  <li key={m.fecha} className="fila" style={{ justifyContent: 'space-between', padding: '8px 0', borderTop: '1px solid var(--border)' }}>
                    <span className="muted">{fecha(m.fecha)}</span>
                    <span>{m.peso_kg != null ? `${m.peso_kg} kg` : ''}{m.grasa_pct != null ? ` · ${m.grasa_pct}% grasa` : ''}{m.masa_muscular_kg != null ? ` · ${m.masa_muscular_kg} kg músculo` : ''}</span>
                  </li>
                ))}
              </ul>
            )}
          </form>

          <section className="card stack" aria-labelledby="priv">
            <div className="fila" style={{ justifyContent: 'space-between' }}>
              <h2 id="priv" style={{ fontSize: 17 }}>Privacidad</h2>
              {estado && <Insignia tono={estado === 'aceptado' ? 'ok' : estado === 'rechazado' ? 'peligro' : 'neutro'}>
                {estado === 'aceptado' ? 'Datos de salud: permitidos' : estado === 'rechazado' ? 'Datos de salud: no permitidos' : 'Sin decidir'}</Insignia>}
            </div>
            {estado === 'aceptado'
              ? <>
                  <p className="muted" style={{ fontSize: 13.5 }}>Si retiras tu permiso, borramos tu peso, medidas y lesiones. Esta acción no se puede deshacer.</p>
                  <button className="btn btn-claro" disabled={ocupado} onClick={() => cambiarConsentimiento(false)}>Retirar mi consentimiento</button>
                </>
              : <button className="btn btn-claro" disabled={ocupado} onClick={() => nav('/consentimiento?volver=/perfil')}>Revisar y aceptar</button>}
          </section>

          <button className="btn btn-claro" onClick={() => { logout(); nav('/login', { replace: true }); }}><IconLogOut width={18} height={18} /> Cerrar sesión</button>

          <section className="card stack" style={{ borderColor: 'var(--danger-tint)' }}>
            <h2 style={{ fontSize: 15, color: 'var(--danger)' }}>Eliminar mi cuenta</h2>
            <p className="muted" style={{ fontSize: 13.5 }}>Borra tu cuenta y todos tus datos para siempre.</p>
            {!confirmaBorrar
              ? <button className="btn btn-claro" onClick={() => setConfirmaBorrar(true)}><IconTrash width={18} height={18} /> Eliminar cuenta</button>
              : <>
                  <Aviso>¿Seguro? No se puede deshacer.</Aviso>
                  <button className="btn btn-peligro" disabled={ocupado} onClick={borrarCuenta}>Sí, eliminar todo</button>
                  <button className="btn btn-claro" onClick={() => setConfirmaBorrar(false)}>No, volver</button>
                </>}
          </section>
        </div>
      </div>
    </div>
  );
}
