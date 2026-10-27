import { Link } from 'react-router';

export default function NoEncontrada() {
  return (
    <div className="oscura pantalla-sin-nav" style={{ display: 'grid', placeItems: 'center', textAlign: 'center' }}>
      <div>
        <div style={{ fontFamily: 'var(--font-sora)', fontWeight: 800, fontSize: 72, color: 'var(--neon)', lineHeight: 1 }}>404</div>
        <p className="muted" style={{ margin: '12px 0 24px' }}>Esta pantalla no existe.</p>
        <Link to="/" className="btn btn-neon" style={{ width: 'auto' }}>Volver al inicio</Link>
      </div>
    </div>
  );
}
