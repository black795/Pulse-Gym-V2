import { useState } from 'react';
import { useNavigate } from 'react-router';
import { IconFlash, IconImage, IconX } from '../../components/Icons';

export default function MobileCamera() {
  const navigate = useNavigate();
  const [flash, setFlash] = useState(false);
  const [captured, setCaptured] = useState(false);
  const [count, setCount] = useState(0);
  const [photos, setPhotos] = useState<string[]>([]);

  const shoot = () => {
    setCaptured(true);
    setCount(c => c + 1);
    setPhotos(p => ['https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=80&h=80&fit=crop&auto=format', ...p]);
    setTimeout(() => {
      setCaptured(false);
      navigate('/mobile/confirm');
    }, 600);
  };

  return (
    <div style={{
      width: '100%', height: '100vh', background: '#000',
      display: 'flex', flexDirection: 'column', position: 'relative',
    }}>
      {/* Flash overlay */}
      {captured && (
        <div style={{ position: 'absolute', inset: 0, background: '#fff', opacity: 0.7, zIndex: 10, transition: 'opacity 0.3s' }} />
      )}

      {/* Viewfinder */}
      <div style={{
        flex: 1, position: 'relative', overflow: 'hidden',
        backgroundImage: 'url(https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=600&h=900&fit=crop&auto=format)',
        backgroundSize: 'cover', backgroundPosition: 'center',
      }}>
        {/* Corner guides */}
        {['tl', 'tr', 'bl', 'br'].map(pos => {
          const top = pos.startsWith('t') ? 60 : undefined;
          const bottom = pos.startsWith('b') ? 60 : undefined;
          const left = pos.endsWith('l') ? 60 : undefined;
          const right = pos.endsWith('r') ? 60 : undefined;
          return (
            <div key={pos} style={{ position: 'absolute', top, bottom, left, right, width: 36, height: 36 }}>
              <svg width="36" height="36" fill="none" stroke="white" strokeWidth="2.5">
                {pos.includes('t') && pos.includes('l') && <><path d="M0 18 L0 0 L18 0" /></>}
                {pos.includes('t') && pos.includes('r') && <><path d="M18 0 L36 0 L36 18" /></>}
                {pos.includes('b') && pos.includes('l') && <><path d="M0 18 L0 36 L18 36" /></>}
                {pos.includes('b') && pos.includes('r') && <><path d="M18 36 L36 36 L36 18" /></>}
              </svg>
            </div>
          );
        })}

        {/* Close + flash */}
        <div style={{ position: 'absolute', top: 16, left: 16, right: 16, display: 'flex', justifyContent: 'space-between' }}>
          <button onClick={() => navigate('/mobile')} style={{ background: 'rgba(0,0,0,0.5)', border: 'none', borderRadius: '50%', width: 38, height: 38, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <IconX style={{ color: '#fff', width: 18, height: 18 }} />
          </button>
          <button onClick={() => setFlash(!flash)} style={{
            background: flash ? 'var(--neon)' : 'rgba(0,0,0,0.5)', border: 'none', borderRadius: '50%',
            width: 38, height: 38, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <IconFlash style={{ color: flash ? 'var(--sidebar)' : '#fff', width: 18, height: 18 }} />
          </button>
        </div>

        {/* Counter */}
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
          <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, fontFamily: 'var(--font-sora)', fontWeight: 700 }}>
            Apunta a la máquina
          </div>
        </div>

        {/* Photo reel */}
        <div style={{ position: 'absolute', bottom: 16, left: 16, display: 'flex', gap: 6 }}>
          {photos.slice(0, 4).map((p, i) => (
            <img key={i} src={p} style={{ width: 44, height: 44, borderRadius: 8, objectFit: 'cover', border: '2px solid #fff' }} />
          ))}
          {count > 0 && (
            <div style={{ width: 44, height: 44, borderRadius: 8, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ color: '#fff', fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 14 }}>{count}</span>
            </div>
          )}
        </div>
      </div>

      {/* Controls */}
      <div style={{ height: 120, background: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-around', padding: '0 40px' }}>
        <button style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <IconImage style={{ color: '#fff', width: 28, height: 28 }} />
          <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: 10 }}>Galería</span>
        </button>

        {/* Shutter */}
        <button onClick={shoot} style={{
          width: 72, height: 72, borderRadius: '50%',
          background: '#fff', border: '4px solid rgba(255,255,255,0.3)',
          cursor: 'pointer', outline: 'none',
          transition: 'transform 0.1s',
          transform: captured ? 'scale(0.9)' : 'scale(1)',
        }} />

        <button style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 24 }}>↺</span>
          <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: 10 }}>Voltear</span>
        </button>
      </div>
    </div>
  );
}
