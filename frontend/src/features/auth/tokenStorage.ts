/** La sesión dura 30 días en el celular: el token se guarda en localStorage hasta que la persona cierre sesión. */
const CLAVE = 'pulse_gym_token';

function seguro<T>(fn: () => T, porDefecto: T): T {
  try { return fn(); } catch { return porDefecto; } // navegación privada u otros bloqueos
}

export const tokenStorage = {
  leer: (): string | null => seguro(() => localStorage.getItem(CLAVE), null),
  guardar: (token: string) => seguro(() => localStorage.setItem(CLAVE, token), undefined),
  borrar: () => seguro(() => localStorage.removeItem(CLAVE), undefined),
};
