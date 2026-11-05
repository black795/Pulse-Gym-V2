/**
 * Mi plan semanal (PG-20, PG-23 a PG-27): elegir los días, ver la semana completa antes de empezar, entender por qué
 * tocó cada ejercicio y regenerarla (máximo 3 veces al día).
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { IconCalendar, IconClock, IconRefresh, IconShield, IconZap } from '../components/Icons';
import { Aviso, Insignia } from '../components/UI';
import { planApi } from '../lib/endpoints';
import { ApiError } from '../lib/http';
import type { DiaSemana, PlanEstado, RutinaDia } from '../lib/tipos';

export const DIAS: { valor: DiaSemana; corto: string }[] = [
  { valor: 'lunes', corto: 'Lun' }, { valor: 'martes', corto: 'Mar' }, { valor: 'miercoles', corto: 'Mié' },
  { valor: 'jueves', corto: 'Jue' }, { valor: 'viernes', corto: 'Vie' }, { valor: 'sabado', corto: 'Sáb' },
  { valor: 'domingo', corto: 'Dom' },
];
const DIA_DE_HOY = DIAS[(new Date().getDay() + 6) % 7].valor; // getDay(): 0 = domingo

/** 90 → "1:30 min", 45 → "45 s". */
export const descanso = (seg: number) => (seg < 60 ? `${seg} s` : `${Math.floor(seg / 60)}:${String(seg % 60).padStart(2, '0')} min`);
export const repeticiones = (min: number, max: number) => (min === max ? `${min}` : `${min}–${max}`);
const ORIGEN = { ia: 'IA', mixto: 'IA + reglas', reglas: 'Reglas' };
export const EQUIPO: Record<string, string> = { maquina: 'Máquina', peso_libre: 'Peso libre', sin_equipo: 'Sin equipo' };

export default function Plan() {
  const [estado, setEstado] = useState<PlanEstado | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [armando, setArmando] = useState(false);
  const [dias, setDias] = useState<DiaSemana[]>([]);
  const [editarDias, setEditarDias] = useState(false);
  const [diaVisto, setDiaVisto] = useState<DiaSemana | null>(null);

  function recibir(e: PlanEstado) {
    setEstado(e);
    // Los sugeridos son los del plan actual, salvo que hayas cambiado los días por semana en tu perfil.
    setDias(e.dias_sugeridos.length ? e.dias_sugeridos : e.plan?.dias.map(d => d.dia) ?? []);
    const diasPlan = e.plan?.dias.map(d => d.dia) ?? [];
    setDiaVisto(v => (v && diasPlan.includes(v) ? v : diasPlan.includes(DIA_DE_HOY) ? DIA_DE_HOY : diasPlan[0] ?? null));
  }

  useEffect(() => {
    planApi.ver().then(recibir).catch(e => setError(e.message)).finally(() => setCargando(false));
  }, []);

  async function armar() {
    setError(null); setArmando(true);
    try { recibir(await planApi.generar(dias)); setEditarDias(false); }
    catch (e) {
      setError(e instanceof ApiError && e.codigo === 'tiempo_agotado'
        ? 'El servidor tardó demasiado. Intenta de nuevo en un momento.'
        : e instanceof Error ? e.message : 'No se pudo armar el plan.');
    } finally { setArmando(false); }
  }

  const alternarDia = (d: DiaSemana) => setDias(l => (l.includes(d) ? l.filter(x => x !== d) : [...l, d]));
  const plan = estado?.plan;
  const dia = plan?.dias.find(d => d.dia === diaVisto) ?? null;

  if (cargando) return <div className="pantalla"><p className="muted pulse-latido" style={{ paddingTop: 40, textAlign: 'center' }}>Cargando tu plan…</p></div>;

  return (
    <div className="pantalla stack" style={{ gap: 16 }}>
      <header className="stack" style={{ gap: 6, paddingTop: 8 }}>
        <div className="fila" style={{ justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <div className="fila" style={{ flexWrap: 'wrap' }}>
            <h1 style={{ fontSize: 24 }}>Mi plan semanal</h1>
            {plan && <Insignia tono={plan.origen === 'reglas' ? 'neutro' : 'ok'}>Versión {plan.version} · {ORIGEN[plan.origen]}</Insignia>}
          </div>
          {plan && !editarDias && <BotonRegenerar className="solo-escritorio btn-auto" restantes={estado!.regeneraciones_restantes} disabled={armando} onClick={() => setEditarDias(true)} />}
        </div>
        {!plan && <p className="muted" style={{ fontSize: 14 }}>Elige qué días entrenas y armamos tu semana según tu objetivo, tu cuerpo y tus lesiones.</p>}
      </header>
      {error && <Aviso>{error}</Aviso>}

      {estado && !estado.puede_generar && (
        <div className="card stack" style={{ gap: 10 }}>
          <h2 style={{ fontSize: 17 }}>Primero completa tu perfil</h2>
          <p className="muted" style={{ fontSize: 14 }}>Necesitamos tu objetivo, nivel, días y minutos por sesión.</p>
          <Link to="/onboarding" className="btn">Completar perfil</Link>
        </div>
      )}

      {plan && plan.lesiones.length > 0 && (
        <div className="aviso aviso-info fila" style={{ alignItems: 'flex-start' }}>
          <IconShield width={20} height={20} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>
            <b>Escudo de lesión activo:</b>{' '}
            {plan.lesiones.map(l => `${l.nombre} (${l.estado === 'activa' ? 'activa' : 'en recuperación'})`).join(', ')}.
            {' '}Quitamos {plan.ejercicios_excluidos} {plan.ejercicios_excluidos === 1 ? 'ejercicio que podía' : 'ejercicios que podían'} empeorarla.
          </span>
        </div>
      )}

      {plan && estado?.perfil_cambio && !editarDias && (
        <div className="card stack" style={{ gap: 8, borderColor: 'var(--primary)' }}>
          <p style={{ fontSize: 14 }}><b>Cambiaste tus datos.</b> ¿Quieres una nueva versión del plan con estos cambios?</p>
          <button className="btn" disabled={armando || estado.regeneraciones_restantes === 0} onClick={() => setEditarDias(true)}>
            <IconRefresh width={18} height={18} /> Actualizar mi plan
          </button>
        </div>
      )}

      {estado?.puede_generar && (!plan || editarDias) && (
        <div className="card stack">
          <h2 style={{ fontSize: 17 }}>{plan ? 'Regenerar el plan' : '¿Qué días entrenas?'}</h2>
          <div className="chips" role="group" aria-label="Días de entrenamiento">
            {DIAS.map(d => (
              <button key={d.valor} type="button" className="chip" aria-pressed={dias.includes(d.valor)} onClick={() => alternarDia(d.valor)}>{d.corto}</button>
            ))}
          </div>
          <p className="muted" style={{ fontSize: 13 }}>
            {dias.length === 0 ? 'Elige al menos un día.' : `${dias.length} ${dias.length === 1 ? 'día' : 'días'} por semana.`}
            {plan && ` Te quedan ${estado.regeneraciones_restantes} de ${estado.regeneraciones_max} regeneraciones hoy.`}
          </p>
          {armando && <Aviso tipo="info">La IA está armando tu semana. Puede tardar hasta 20 segundos…</Aviso>}
          <button className="btn" disabled={armando || dias.length === 0 || (!!plan && estado.regeneraciones_restantes === 0)} onClick={armar}>
            <IconZap width={18} height={18} /> {armando ? 'Armando…' : plan ? 'Regenerar con estos días' : 'Armar mi plan'}
          </button>
          {plan && !armando && <button className="btn btn-texto" style={{ alignSelf: 'center' }} onClick={() => setEditarDias(false)}>Cancelar</button>}
        </div>
      )}

      {plan && (
        <>
          <section className="card stack" style={{ gap: 8, borderColor: 'var(--neon)', boxShadow: '0 0 0 3px rgba(182,255,69,.18)' }}>
            <h2 style={{ fontSize: 16 }}>Por qué este plan</h2>
            <p style={{ fontSize: 14, lineHeight: 1.5 }}>{plan.explicacion}</p>
            <p className="muted" style={{ fontSize: 12.5 }}>
              Esquema: {plan.esquema_texto}.{plan.modelo ? ` Armado por ${plan.modelo === 'simulada' ? 'la IA simulada' : plan.modelo} en ${(plan.duracion_ms / 1000).toFixed(1)} s.` : ''}
            </p>
          </section>

          {plan.avisos.map(a => <Aviso key={a} tipo="info">{a}</Aviso>)}

          <div className="tabs-dias" role="tablist" aria-label="Días del plan">
            {plan.dias.map(d => (
              <button key={d.dia} role="tab" aria-selected={d.dia === diaVisto} className="tab-dia" onClick={() => setDiaVisto(d.dia)}>
                <b>{DIAS.find(x => x.valor === d.dia)?.corto}{d.dia === DIA_DE_HOY ? ' · hoy' : ''}</b>
                <span>{d.enfoque.split(':')[0]}</span>
              </button>
            ))}
          </div>

          {dia && <DiaDelPlan dia={dia} />}

          {!editarDias && <BotonRegenerar className="solo-movil" restantes={estado!.regeneraciones_restantes} disabled={armando} onClick={() => setEditarDias(true)} />}
        </>
      )}
    </div>
  );
}

function BotonRegenerar({ className, restantes, disabled, onClick }: { className: string; restantes: number; disabled: boolean; onClick: () => void }) {
  return (
    <button className={`btn btn-claro ${className}`} disabled={disabled || restantes === 0} onClick={onClick}>
      <IconRefresh width={18} height={18} />
      {restantes === 0 ? 'Ya regeneraste 3 veces hoy' : `Regenerar o cambiar días (quedan ${restantes})`}
    </button>
  );
}

function DiaDelPlan({ dia }: { dia: RutinaDia }) {
  return (
    <section className="stack" style={{ gap: 10 }} aria-label={`${dia.dia_nombre}: ${dia.enfoque}`}>
      <div className="stack" style={{ gap: 4 }}>
        <h2 style={{ fontSize: 18 }}>{dia.dia_nombre} · {dia.enfoque}</h2>
        <p className="muted fila" style={{ fontSize: 13, gap: 6 }}>
          <IconCalendar width={15} height={15} /> {dia.ejercicios.length} ejercicios
          <IconClock width={15} height={15} style={{ marginLeft: 6 }} /> ~{dia.minutos_estimados} min
        </p>
        {dia.explicacion && <p style={{ fontSize: 13.5, lineHeight: 1.45 }}>{dia.explicacion}</p>}
      </div>
      <div className="grilla-ejercicios">
        {dia.ejercicios.map(e => (
          <article key={e.id} className="card ejercicio">
            <span className="ejercicio-orden">{e.orden}</span>
            <div className="stack" style={{ gap: 4, minWidth: 0 }}>
              <div className="fila" style={{ gap: 8, flexWrap: 'wrap' }}>
                <b style={{ fontSize: 15 }}>{e.ejercicio.nombre}</b>
                {e.precaucion && <Insignia tono="aviso">Con precaución</Insignia>}
              </div>
              <span className="muted" style={{ fontSize: 12.5 }}>
                {e.ejercicio.musculo_principal} · {e.ejercicio.maquinas.length ? e.ejercicio.maquinas.join(' o ') : EQUIPO[e.ejercicio.categoria_equipo]}
              </span>
              <span style={{ fontSize: 14, fontWeight: 700 }}>
                {e.series} series × {repeticiones(e.reps_min, e.reps_max)} reps · descanso {descanso(e.descanso_seg)}
              </span>
              {e.motivo && <span className="muted" style={{ fontSize: 13 }}>{e.motivo}</span>}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
