/**
 * PG-07: si se corta la conexión, la foto queda en espera y se sube al volver la señal.
 * Cada foto se guarda en IndexedDB (dentro del celular) hasta que el servidor la recibe; así tampoco se pierde
 * si el usuario cierra la app en el gym. Solo guarda la foto ya reducida, nunca datos de la cuenta.
 */
const BD = 'pulse-gym';
const ALMACEN = 'fotos-pendientes';

export interface FotoPendiente { clave: string; gymId: number; foto: Blob; creada: number }

function abrir(): Promise<IDBDatabase> {
  return new Promise((resolver, rechazar) => {
    const pedido = indexedDB.open(BD, 1);
    pedido.onupgradeneeded = () => pedido.result.createObjectStore(ALMACEN, { keyPath: 'clave' });
    pedido.onsuccess = () => resolver(pedido.result);
    pedido.onerror = () => rechazar(pedido.error);
  });
}

async function operar<T>(modo: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const bd = await abrir();
  try {
    return await new Promise<T>((resolver, rechazar) => {
      const pedido = fn(bd.transaction(ALMACEN, modo).objectStore(ALMACEN));
      pedido.onsuccess = () => resolver(pedido.result);
      pedido.onerror = () => rechazar(pedido.error);
    });
  } finally {
    bd.close();
  }
}

// Si IndexedDB no está disponible (modo privado de algunos navegadores), la app sigue funcionando sin la cola.
export const colaFotos = {
  guardar: (p: FotoPendiente) => operar('readwrite', s => s.put(p)).then(() => true).catch(() => false),
  quitar: (clave: string) => operar('readwrite', s => s.delete(clave)).catch(() => undefined),
  delGym: async (gymId: number): Promise<FotoPendiente[]> => {
    try {
      const todas = await operar<FotoPendiente[]>('readonly', s => s.getAll());
      return todas.filter(p => p.gymId === gymId).sort((a, b) => a.creada - b.creada);
    } catch {
      return [];
    }
  },
};
