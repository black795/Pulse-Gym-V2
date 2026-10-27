/**
 * PG-07: cámara dentro de la app con guía de encuadre, en "modo recorrido" (varias fotos seguidas sin cerrarla).
 * Si el navegador no permite abrirla (permiso negado o página sin HTTPS), explica qué hacer y ofrece
 * la cámara del sistema o la galería.
 */
import { useEffect, useRef, useState } from 'react';
import { IconCamera, IconCheck, IconImage, IconX } from './Icons';
import { MAX_PX } from '../lib/imagen';

type Estado = 'abriendo' | 'lista' | 'denegada' | 'sin_camara' | 'no_soportada';

export default function Camara({ tomadas, onFoto, onGaleria, onCamaraSistema, onCerrar }: {
  tomadas: number;
  onFoto: (foto: Blob) => void;
  onGaleria: () => void;
  onCamaraSistema: () => void;
  onCerrar: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const [estado, setEstado] = useState<Estado>('abriendo');
  const [flash, setFlash] = useState(false);
  const [intento, setIntento] = useState(0);
  const [tarda, setTarda] = useState(false);

  // Si el permiso queda sin responder o la cámara está ocupada por otra app, no dejar al usuario esperando.
  useEffect(() => {
    if (estado !== 'abriendo') { setTarda(false); return; }
    const t = setTimeout(() => setTarda(true), 8000);
    return () => clearTimeout(t);
  }, [estado, intento]);

  useEffect(() => {
    // getUserMedia solo funciona con HTTPS (o en localhost). Desde el celular por wifi (http://192.168…) no.
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) { setEstado('no_soportada'); return; }
    let flujo: MediaStream | null = null;
    let activo = true;
    setEstado('abriendo');
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1440 } }, audio: false })
      .then(f => {
        if (!activo) { f.getTracks().forEach(t => t.stop()); return; }
        flujo = f;
        if (video.current) { video.current.srcObject = f; void video.current.play().catch(() => {}); }
        setEstado('lista');
      })
      .catch((e: DOMException) => {
        if (!activo) return;
        setEstado(e.name === 'NotAllowedError' || e.name === 'SecurityError' ? 'denegada' : e.name === 'NotFoundError' || e.name === 'OverconstrainedError' ? 'sin_camara' : 'no_soportada');
      });
    return () => { activo = false; flujo?.getTracks().forEach(t => t.stop()); };
  }, [intento]);

  function disparar() {
    const v = video.current;
    if (!v || !v.videoWidth) return;
    const escala = Math.min(1, MAX_PX / Math.max(v.videoWidth, v.videoHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(v.videoWidth * escala);
    canvas.height = Math.round(v.videoHeight * escala);
    canvas.getContext('2d')!.drawImage(v, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(b => { if (b) onFoto(b); }, 'image/jpeg', 0.85);
    setFlash(true);
    setTimeout(() => setFlash(false), 150);
  }

  return (
    <div className="camara" role="dialog" aria-modal="true" aria-label="Cámara">
      <div className="camara-visor">
        <video ref={video} playsInline muted autoPlay aria-hidden="true" />
        {estado === 'lista' && <>
          <div className="camara-guia" />
          <p className="camara-texto">Encuadra la máquina completa · que no salgan otras personas</p>
        </>}
        {flash && <div className="camara-flash" />}
        {estado !== 'lista' && (
          <div className="stack" style={{ position: 'absolute', inset: 0, padding: 24, justifyContent: 'center', textAlign: 'center' }}>
            {estado === 'abriendo' && <p>Abriendo la cámara…</p>}
            {estado === 'abriendo' && tarda && <>
              <p style={{ fontSize: 14, color: '#c9d6cd' }}>¿No se abre? Acepta el permiso de cámara si te lo pide, o cierra otras apps que la estén usando.</p>
              <button className="btn btn-neon" onClick={onCamaraSistema}><IconCamera width={18} height={18} /> Usar la cámara del celular</button>
              <button className="btn btn-claro" onClick={onGaleria}><IconImage width={18} height={18} /> Elegir de la galería</button>
            </>}
            {estado === 'denegada' && <>
              <h2 style={{ fontSize: 19 }}>No tenemos permiso para usar la cámara</h2>
              <p style={{ fontSize: 14, color: '#c9d6cd', lineHeight: 1.5 }}>
                <b>Android (Chrome):</b> toca el candado junto a la dirección → Permisos → Cámara → Permitir.<br />
                <b>iPhone (Safari):</b> toca «aA» en la barra → Configuración del sitio web → Cámara → Permitir.<br />
                Luego vuelve a intentarlo, o sube fotos desde tu galería.
              </p>
              <button className="btn btn-neon" onClick={() => setIntento(i => i + 1)}>Volver a intentar</button>
            </>}
            {estado === 'sin_camara' && <h2 style={{ fontSize: 19 }}>No encontramos una cámara en este dispositivo</h2>}
            {estado === 'no_soportada' && <>
              <h2 style={{ fontSize: 19 }}>Este navegador no abre la cámara dentro de la app</h2>
              <p style={{ fontSize: 14, color: '#c9d6cd' }}>Usa la cámara de tu celular: igual puedes tomar varias fotos, una tras otra.</p>
              <button className="btn btn-neon" onClick={onCamaraSistema}><IconCamera width={18} height={18} /> Abrir la cámara del celular</button>
            </>}
            {estado !== 'abriendo' && (
              <button className="btn btn-claro" onClick={onGaleria}><IconImage width={18} height={18} /> Elegir de la galería</button>
            )}
          </div>
        )}
      </div>

      <div className="camara-controles">
        <button className="camara-boton" onClick={onGaleria} aria-label="Elegir fotos de la galería">
          <IconImage width={26} height={26} />Galería
        </button>
        {estado === 'lista'
          ? <button className="obturador" onClick={disparar} aria-label="Tomar foto" />
          : <button className="camara-boton" onClick={onCerrar} aria-label="Cerrar la cámara"><IconX width={26} height={26} />Cerrar</button>}
        <button className="camara-boton" onClick={onCerrar} aria-label={`Listo, ${tomadas} fotos tomadas`}>
          <IconCheck width={26} height={26} style={{ color: 'var(--neon)' }} />Listo{tomadas > 0 ? ` (${tomadas})` : ''}
        </button>
      </div>
    </div>
  );
}
