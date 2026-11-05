/**
 * PG-36: el aviso sonoro del fin del descanso, generado con Web Audio (sin archivos de sonido).
 * Los navegadores del celular solo dejan sonar audio después de un toque del usuario: por eso `preparar()` se llama
 * al tocar "✓ Listo", y el pitido de verdad suena después, cuando termina el descanso.
 */
let ctx: AudioContext | null = null;

export function preparar() {
  try {
    ctx ??= new AudioContext();
    if (ctx.state === 'suspended') void ctx.resume();
  } catch { /* sin Web Audio: el descanso sigue funcionando, solo que en silencio */ }
}

/** Tres pitidos cortos. */
export function pitido() {
  if (!ctx) return;
  try {
    const t0 = ctx.currentTime;
    for (let i = 0; i < 3; i++) {
      const osc = ctx.createOscillator();
      const vol = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = i === 2 ? 1320 : 880;
      const t = t0 + i * 0.28;
      vol.gain.setValueAtTime(0.0001, t);
      vol.gain.exponentialRampToValueAtTime(0.35, t + 0.02);
      vol.gain.exponentialRampToValueAtTime(0.0001, t + 0.22);
      osc.connect(vol).connect(ctx.destination);
      osc.start(t);
      osc.stop(t + 0.24);
    }
  } catch { /* nada */ }
}
