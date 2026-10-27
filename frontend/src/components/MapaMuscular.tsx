/**
 * Mapa anatómico del cuerpo humano (vista anterior y posterior).
 * Resalta en color verde el músculo principal trabajado y en color ámbar los músculos secundarios.
 */
import React from 'react';

interface Props {
  musculoPrincipal?: string | null;
  musculosSecundarios?: string[];
  ancho?: number;
  alto?: number;
  /** Texto de la leyenda ámbar (por defecto "Secundario"). */
  textoSecundario?: string;
}

const NOMBRES_GRUPOS: Record<string, string> = {
  pecho: 'Pecho',
  espalda: 'Espalda',
  hombros: 'Hombros',
  biceps: 'Bíceps',
  triceps: 'Tríceps',
  cuadriceps: 'Cuádriceps',
  isquiotibiales: 'Isquiotibiales',
  gluteos: 'Glúteos',
  pantorrillas: 'Pantorrillas',
  core: 'Core y abdomen',
  cardio: 'Cardiovascular',
};

export default function MapaMuscular({
  musculoPrincipal,
  musculosSecundarios = [],
  ancho = 260,
  alto = 280,
  textoSecundario = 'Secundario',
}: Props) {
  const principal = musculoPrincipal?.toLowerCase() ?? '';
  const secundarios = musculosSecundarios.map(m => m.toLowerCase());

  function obtenerColor(grupo: string): { fill: string; stroke: string; activo: boolean } {
    if (principal === grupo) {
      return { fill: '#16A34A', stroke: '#15803D', activo: true }; // Verde primario
    }
    if (secundarios.includes(grupo)) {
      return { fill: '#F59E0B', stroke: '#D97706', activo: true }; // Ámbar secundario
    }
    return { fill: '#E2E8F0', stroke: '#CBD5E1', activo: false }; // Inactivo
  }

  const cPecho = obtenerColor('pecho');
  const cEspalda = obtenerColor('espalda');
  const cHombros = obtenerColor('hombros');
  const cBiceps = obtenerColor('biceps');
  const cTriceps = obtenerColor('triceps');
  const cCore = obtenerColor('core');
  const cCuadriceps = obtenerColor('cuadriceps');
  const cIsquios = obtenerColor('isquiotibiales');
  const cGluteos = obtenerColor('gluteos');
  const cPantorrillas = obtenerColor('pantorrillas');

  return (
    <div className="card stack" style={{ gap: 12, alignItems: 'center', background: '#F8FAFC', padding: 14 }}>
      <div style={{ display: 'flex', gap: 18, justifyContent: 'center' }}>
        {/* VISTA ANTERIOR (FRENTE) */}
        <div style={{ textAlign: 'center' }}>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--muted)', letterSpacing: 0.5 }}>Frente</span>
          <svg viewBox="0 0 100 200" width={ancho / 2} height={alto} style={{ display: 'block', margin: '4px auto 0' }}>
            {/* Cabeza y cuello */}
            <circle cx="50" cy="18" r="10" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.5" />
            <path d="M 46 28 L 54 28 L 54 34 L 46 34 Z" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.5" />

            {/* Hombros frontales */}
            <path d="M 33 35 Q 26 38 23 48 Q 30 46 34 42 Z" fill={cHombros.fill} stroke={cHombros.stroke} strokeWidth="1.5" />
            <path d="M 67 35 Q 74 38 77 48 Q 70 46 66 42 Z" fill={cHombros.fill} stroke={cHombros.stroke} strokeWidth="1.5" />

            {/* Pecho (Pectorales) */}
            <path d="M 36 37 Q 50 39 49 54 Q 38 55 35 45 Z" fill={cPecho.fill} stroke={cPecho.stroke} strokeWidth="1.5" />
            <path d="M 64 37 Q 50 39 51 54 Q 62 55 65 45 Z" fill={cPecho.fill} stroke={cPecho.stroke} strokeWidth="1.5" />

            {/* Bíceps y brazos */}
            <path d="M 22 50 Q 18 63 21 76 Q 26 73 26 56 Z" fill={cBiceps.fill} stroke={cBiceps.stroke} strokeWidth="1.5" />
            <path d="M 78 50 Q 82 63 79 76 Q 74 73 74 56 Z" fill={cBiceps.fill} stroke={cBiceps.stroke} strokeWidth="1.5" />
            {/* Antebrazos y manos */}
            <path d="M 20 78 Q 17 92 18 104 Q 22 104 24 88 Z" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.5" />
            <path d="M 80 78 Q 83 92 82 104 Q 78 104 76 88 Z" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.5" />

            {/* Abdomen / Core */}
            <path d="M 40 57 Q 50 56 60 57 L 58 84 Q 50 87 42 84 Z" fill={cCore.fill} stroke={cCore.stroke} strokeWidth="1.5" />

            {/* Pelvis */}
            <path d="M 41 86 Q 50 88 59 86 L 56 98 Q 50 101 44 98 Z" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.5" />

            {/* Cuádriceps (Piernas frontales) */}
            <path d="M 37 100 Q 32 120 36 142 Q 44 142 47 114 Q 44 100 37 100 Z" fill={cCuadriceps.fill} stroke={cCuadriceps.stroke} strokeWidth="1.5" />
            <path d="M 63 100 Q 68 120 64 142 Q 56 142 53 114 Q 56 100 63 100 Z" fill={cCuadriceps.fill} stroke={cCuadriceps.stroke} strokeWidth="1.5" />

            {/* Rodillas */}
            <circle cx="39" cy="147" r="3.5" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.2" />
            <circle cx="61" cy="147" r="3.5" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.2" />

            {/* Pantorrillas frontales */}
            <path d="M 36 152 Q 33 168 37 186 Q 42 186 42 165 Z" fill={cPantorrillas.fill} stroke={cPantorrillas.stroke} strokeWidth="1.5" />
            <path d="M 64 152 Q 67 168 63 186 Q 58 186 58 165 Z" fill={cPantorrillas.fill} stroke={cPantorrillas.stroke} strokeWidth="1.5" />
            {/* Pies */}
            <path d="M 36 188 Q 32 195 38 198 Q 44 196 41 188 Z" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.2" />
            <path d="M 64 188 Q 68 195 62 198 Q 56 196 59 188 Z" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.2" />
          </svg>
        </div>

        {/* VISTA POSTERIOR (ESPALDA) */}
        <div style={{ textAlign: 'center' }}>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--muted)', letterSpacing: 0.5 }}>Espalda</span>
          <svg viewBox="0 0 100 200" width={ancho / 2} height={alto} style={{ display: 'block', margin: '4px auto 0' }}>
            {/* Cabeza y cuello posterior */}
            <circle cx="50" cy="18" r="10" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.5" />
            <path d="M 46 28 L 54 28 L 54 34 L 46 34 Z" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.5" />

            {/* Trapecios y Espalda alta / Dorsales */}
            <path d="M 45 34 L 55 34 L 64 42 Q 67 62 57 80 L 50 82 L 43 80 Q 33 62 36 42 Z" fill={cEspalda.fill} stroke={cEspalda.stroke} strokeWidth="1.5" />

            {/* Hombros posteriores */}
            <path d="M 34 38 Q 26 42 24 50 Q 30 48 35 44 Z" fill={cHombros.fill} stroke={cHombros.stroke} strokeWidth="1.5" />
            <path d="M 66 38 Q 74 42 76 50 Q 70 48 65 44 Z" fill={cHombros.fill} stroke={cHombros.stroke} strokeWidth="1.5" />

            {/* Tríceps */}
            <path d="M 23 52 Q 19 65 22 78 Q 27 75 27 58 Z" fill={cTriceps.fill} stroke={cTriceps.stroke} strokeWidth="1.5" />
            <path d="M 77 52 Q 81 65 78 78 Q 73 75 73 58 Z" fill={cTriceps.fill} stroke={cTriceps.stroke} strokeWidth="1.5" />
            {/* Antebrazos posteriores */}
            <path d="M 21 80 Q 18 94 19 104 Q 23 104 25 90 Z" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.5" />
            <path d="M 79 80 Q 82 94 81 104 Q 77 104 75 90 Z" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.5" />

            {/* Glúteos */}
            <path d="M 38 84 Q 50 84 49 104 Q 37 105 36 94 Z" fill={cGluteos.fill} stroke={cGluteos.stroke} strokeWidth="1.5" />
            <path d="M 62 84 Q 50 84 51 104 Q 63 105 64 94 Z" fill={cGluteos.fill} stroke={cGluteos.stroke} strokeWidth="1.5" />

            {/* Isquiotibiales (Piernas posteriores) */}
            <path d="M 36 106 Q 33 124 37 142 Q 44 142 47 114 Q 44 106 36 106 Z" fill={cIsquios.fill} stroke={cIsquios.stroke} strokeWidth="1.5" />
            <path d="M 64 106 Q 67 124 63 142 Q 56 142 53 114 Q 56 106 64 106 Z" fill={cIsquios.fill} stroke={cIsquios.stroke} strokeWidth="1.5" />

            {/* Hueco poplíteo */}
            <circle cx="40" cy="147" r="3.5" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.2" />
            <circle cx="60" cy="147" r="3.5" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.2" />

            {/* Pantorrillas posteriores (Gemelos/Sóleo) */}
            <path d="M 35 152 Q 31 168 37 186 Q 44 186 43 165 Z" fill={cPantorrillas.fill} stroke={cPantorrillas.stroke} strokeWidth="1.5" />
            <path d="M 65 152 Q 69 168 63 186 Q 56 186 57 165 Z" fill={cPantorrillas.fill} stroke={cPantorrillas.stroke} strokeWidth="1.5" />
            {/* Talones */}
            <path d="M 37 188 Q 33 194 38 198 Q 43 196 41 188 Z" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.2" />
            <path d="M 63 188 Q 67 194 62 198 Q 57 196 59 188 Z" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1.2" />
          </svg>
        </div>
      </div>

      {/* LEYENDA Y ETIQUETAS */}
      <div className="fila" style={{ gap: 14, fontSize: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
        {principal && (
          <span className="fila" style={{ gap: 6, alignItems: 'center' }}>
            <span style={{ width: 12, height: 12, borderRadius: 3, background: '#16A34A', display: 'inline-block' }} />
            <b>Principal:</b> {NOMBRES_GRUPOS[principal] ?? principal}
          </span>
        )}
        {secundarios.length > 0 && (
          <span className="fila" style={{ gap: 6, alignItems: 'center' }}>
            <span style={{ width: 12, height: 12, borderRadius: 3, background: '#F59E0B', display: 'inline-block' }} />
            <b>{textoSecundario}:</b> {secundarios.map(s => NOMBRES_GRUPOS[s] ?? s).join(', ')}
          </span>
        )}
      </div>
    </div>
  );
}
