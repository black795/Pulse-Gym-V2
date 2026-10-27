/**
 * PG-07: la foto se reduce en el celular ANTES de subirla (máximo 1280 px, JPG): sube más rápido con datos móviles.
 * Al redibujarla en un canvas también se pierden los metadatos (ubicación GPS) de la cámara.
 */
export const MAX_PX = 1280;
export const MAX_MB = 10;
const TIPOS = ['image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp'];
const EXTENSIONES = /\.(jpe?g|png|heic|heif|webp)$/i;

/** null si el archivo sirve; si no, el mensaje para el usuario. */
export function validarArchivo(f: File): string | null {
  // Algunos celulares no informan el tipo de las fotos HEIC: se acepta también por la extensión.
  if (!TIPOS.includes(f.type.toLowerCase()) && !EXTENSIONES.test(f.name)) return `«${f.name}» no es una foto JPG, PNG o HEIC.`;
  if (f.size > MAX_MB * 1024 * 1024) return `«${f.name}» pesa más de ${MAX_MB} MB.`;
  return null;
}

async function decodificar(archivo: Blob): Promise<ImageBitmap | HTMLImageElement> {
  try {
    return await createImageBitmap(archivo, { imageOrientation: 'from-image' });
  } catch {
    // Safari antiguo: se carga como <img>.
    const url = URL.createObjectURL(archivo);
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
      return img;
    } finally {
      URL.revokeObjectURL(url);
    }
  }
}

/**
 * Devuelve un JPG de máximo 1280 px. Si el navegador no sabe abrir el formato (HEIC en Chrome),
 * devuelve el original y el servidor se encarga de reducirlo.
 */
export async function reducirImagen(archivo: Blob): Promise<Blob> {
  let img: ImageBitmap | HTMLImageElement;
  try {
    img = await decodificar(archivo);
  } catch {
    return archivo;
  }
  const ancho = 'naturalWidth' in img ? img.naturalWidth : img.width;
  const alto = 'naturalHeight' in img ? img.naturalHeight : img.height;
  const escala = Math.min(1, MAX_PX / Math.max(ancho, alto));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(ancho * escala);
  canvas.height = Math.round(alto * escala);
  canvas.getContext('2d')!.drawImage(img, 0, 0, canvas.width, canvas.height);
  if ('close' in img) img.close();
  const blob = await new Promise<Blob | null>(r => canvas.toBlob(r, 'image/jpeg', 0.85));
  return blob ?? archivo;
}
