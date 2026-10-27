import { useCallback, useEffect, useState } from 'react';
import { perfilApi } from './endpoints';
import type { Perfil } from './tipos';

/** Carga el perfil y permite recargarlo o reemplazarlo con lo que devuelve el backend tras guardar. */
export function usePerfil() {
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [error, setError] = useState<string | null>(null);
  const recargar = useCallback(() => perfilApi.ver().then(p => { setPerfil(p); setError(null); }).catch(e => setError(e.message)), []);
  useEffect(() => { void recargar(); }, [recargar]);
  return { perfil, setPerfil, error, recargar };
}

export const OBJETIVOS = [
  { valor: 'bajar_grasa', texto: 'Bajar de grasa' }, { valor: 'ganar_musculo', texto: 'Ganar músculo' },
  { valor: 'fuerza', texto: 'Ganar fuerza' }, { valor: 'resistencia', texto: 'Mejorar resistencia' },
  { valor: 'salud_general', texto: 'Salud general' },
];
export const NIVELES = [
  { valor: 'principiante', texto: 'Principiante (empiezo o retomo)' }, { valor: 'intermedio', texto: 'Intermedio (entreno hace meses)' },
  { valor: 'avanzado', texto: 'Avanzado (más de 2 años)' },
];
export const SEXOS = [{ valor: 'masculino', texto: 'Hombre' }, { valor: 'femenino', texto: 'Mujer' }, { valor: 'otro', texto: 'Otro' }];
export const nombreDe = (lista: { valor: string; texto: string }[], v: string | null) => lista.find(o => o.valor === v)?.texto ?? '—';
