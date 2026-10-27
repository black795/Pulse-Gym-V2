-- =============================================================================
-- PULSE GYM V2 — ESQUEMA COMPLETO DE BASE DE DATOS (23 TABLAS EN 5 MÓDULOS)
-- Basado en: Pulse_Gym_Base_de_Datos_v2.drawio y Pulse_Gym_Nuevo_Enfoque_v2.docx
-- Motor: PostgreSQL 16+
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- 0. TIPOS ENUMERADOS (ENUMS)
-- =============================================================================
DO $$ BEGIN
    CREATE TYPE tipo_maquina_enum AS ENUM ('polea', 'palanca_disco', 'selectorizada', 'peso_libre', 'cardio', 'banco_soporte', 'implemento', 'otro');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE dificultad_ejercicio_enum AS ENUM ('principiante', 'intermedio', 'avanzado');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE region_muscular_enum AS ENUM ('tren_superior', 'tren_inferior', 'core', 'cuerpo_completo');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE rol_musculo_enum AS ENUM ('principal', 'secundario');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE nivel_contraindicacion_enum AS ENUM ('evitar', 'precaucion');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE sexo_usuario_enum AS ENUM ('masculino', 'femenino', 'otro', 'prefiero_no_decir');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE nivel_usuario_enum AS ENUM ('principiante', 'intermedio', 'avanzado');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE objetivo_usuario_enum AS ENUM ('perdida_grasa', 'masa_muscular', 'fuerza', 'acondicionamiento', 'salud_general');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE tipo_lesion_enum AS ENUM ('aguda', 'cronica');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE estado_lesion_enum AS ENUM ('activa', 'en_reintroduccion', 'recuperada');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE estado_foto_enum AS ENUM ('pendiente', 'reconocida_alta', 'opciones_sugeridas', 'busqueda_web', 'confirmada', 'descartada');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE estado_propuesta_enum AS ENUM ('pendiente_revision', 'aprobada', 'rechazada');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE estado_gym_maquina_enum AS ENUM ('disponible', 'malograda', 'retirada');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE estado_rutina_enum AS ENUM ('activa', 'archivada');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE dia_semana_enum AS ENUM ('lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE estado_sesion_enum AS ENUM ('en_curso', 'completa', 'parcial', 'manual');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE motivo_ejercicio_sesion_enum AS ENUM ('plan_original', 'adaptado_gym', 'maquina_ocupada', 'sin_equipo', 'molestia_dolor');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;


-- =============================================================================
-- GRUPO 1: CATÁLOGO BASE (LO MANTIENE EL EQUIPO — 8 TABLAS)
-- =============================================================================

-- 1. maquina_catalogo
CREATE TABLE IF NOT EXISTS maquina_catalogo (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(40) UNIQUE NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    alias TEXT[] DEFAULT '{}',
    tipo tipo_maquina_enum NOT NULL,
    descripcion TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

-- 2. maquina_foto_ref
CREATE TABLE IF NOT EXISTS maquina_foto_ref (
    id SERIAL PRIMARY KEY,
    maquina_id INT NOT NULL REFERENCES maquina_catalogo(id) ON DELETE CASCADE,
    url TEXT NOT NULL
);

-- 3. ejercicio
CREATE TABLE IF NOT EXISTS ejercicio (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(40) UNIQUE NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    instrucciones TEXT,
    dificultad dificultad_ejercicio_enum NOT NULL DEFAULT 'principiante',
    es_multiarticular BOOLEAN NOT NULL DEFAULT FALSE,
    sin_equipo BOOLEAN NOT NULL DEFAULT FALSE
);

-- 4. ejercicio_maquina
CREATE TABLE IF NOT EXISTS ejercicio_maquina (
    ejercicio_id INT NOT NULL REFERENCES ejercicio(id) ON DELETE CASCADE,
    maquina_id INT NOT NULL REFERENCES maquina_catalogo(id) ON DELETE CASCADE,
    es_principal BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (ejercicio_id, maquina_id)
);

-- 5. grupo_muscular
CREATE TABLE IF NOT EXISTS grupo_muscular (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(60) UNIQUE NOT NULL,
    region region_muscular_enum NOT NULL
);

-- 6. ejercicio_musculo
CREATE TABLE IF NOT EXISTS ejercicio_musculo (
    ejercicio_id INT NOT NULL REFERENCES ejercicio(id) ON DELETE CASCADE,
    grupo_muscular_id INT NOT NULL REFERENCES grupo_muscular(id) ON DELETE CASCADE,
    rol rol_musculo_enum NOT NULL DEFAULT 'principal',
    PRIMARY KEY (ejercicio_id, grupo_muscular_id)
);

-- 7. zona_lesion
CREATE TABLE IF NOT EXISTS zona_lesion (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(60) UNIQUE NOT NULL
);

-- 8. ejercicio_contraindicacion
CREATE TABLE IF NOT EXISTS ejercicio_contraindicacion (
    ejercicio_id INT NOT NULL REFERENCES ejercicio(id) ON DELETE CASCADE,
    zona_lesion_id INT NOT NULL REFERENCES zona_lesion(id) ON DELETE CASCADE,
    nivel nivel_contraindicacion_enum NOT NULL DEFAULT 'evitar',
    PRIMARY KEY (ejercicio_id, zona_lesion_id)
);


-- =============================================================================
-- GRUPO 2: USUARIO Y PERFIL (4 TABLAS)
-- =============================================================================

-- 9. usuario (Un único rol: la persona que entrena)
CREATE TABLE IF NOT EXISTS usuario (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(160) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    fecha_nacimiento DATE,
    sexo sexo_usuario_enum,
    altura_cm NUMERIC(5,1),
    nivel nivel_usuario_enum DEFAULT 'principiante',
    dias_semana SMALLINT DEFAULT 3 CHECK (dias_semana BETWEEN 1 AND 7),
    minutos_sesion SMALLINT DEFAULT 60 CHECK (minutos_sesion BETWEEN 15 AND 240),
    descanso_default_seg SMALLINT NOT NULL DEFAULT 120,
    consentimiento_at TIMESTAMP,
    creado_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_at TIMESTAMP
);

-- 10. usuario_objetivo
CREATE TABLE IF NOT EXISTS usuario_objetivo (
    id SERIAL PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    objetivo objetivo_usuario_enum NOT NULL,
    prioridad SMALLINT NOT NULL DEFAULT 1,
    UNIQUE (usuario_id, objetivo)
);

-- 11. medicion
CREATE TABLE IF NOT EXISTS medicion (
    id SERIAL PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    peso_kg NUMERIC(5,1) NOT NULL,
    grasa_pct NUMERIC(4,1),
    masa_muscular_kg NUMERIC(5,1),
    cintura_cm NUMERIC(5,1),
    cadera_cm NUMERIC(5,1)
);

-- 12. lesion
CREATE TABLE IF NOT EXISTS lesion (
    id SERIAL PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    zona_lesion_id INT NOT NULL REFERENCES zona_lesion(id) ON DELETE RESTRICT,
    tipo tipo_lesion_enum NOT NULL DEFAULT 'aguda',
    estado estado_lesion_enum NOT NULL DEFAULT 'activa',
    dolor_con_carga BOOLEAN NOT NULL DEFAULT TRUE,
    descripcion TEXT,
    fecha_inicio DATE NOT NULL DEFAULT CURRENT_DATE
);


-- =============================================================================
-- GRUPO 3: MIS GYMS E IA DE FOTOS (5 TABLAS)
-- =============================================================================

-- 13. gym
CREATE TABLE IF NOT EXISTS gym (
    id SERIAL PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    nombre VARCHAR(120) NOT NULL,
    ubicacion VARCHAR(160),
    ultimo_uso_at TIMESTAMP,
    creado_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 14. foto_maquina
CREATE TABLE IF NOT EXISTS foto_maquina (
    id SERIAL PRIMARY KEY,
    gym_id INT NOT NULL REFERENCES gym(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    estado estado_foto_enum NOT NULL DEFAULT 'pendiente',
    tomada_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 15. reconocimiento_ia
CREATE TABLE IF NOT EXISTS reconocimiento_ia (
    id SERIAL PRIMARY KEY,
    foto_id INT NOT NULL REFERENCES foto_maquina(id) ON DELETE CASCADE,
    maquina_id INT NOT NULL REFERENCES maquina_catalogo(id) ON DELETE CASCADE,
    confianza NUMERIC(4,3) NOT NULL CHECK (confianza BETWEEN 0 AND 1),
    puesto SMALLINT NOT NULL,
    modelo VARCHAR(60) NOT NULL
);

-- 16. maquina_propuesta (Hallada en internet, pendiente de revisión por el equipo)
CREATE TABLE IF NOT EXISTS maquina_propuesta (
    id SERIAL PRIMARY KEY,
    foto_id INT NOT NULL REFERENCES foto_maquina(id) ON DELETE CASCADE,
    maquina_similar_id INT REFERENCES maquina_catalogo(id) ON DELETE SET NULL,
    grupo_muscular_id INT REFERENCES grupo_muscular(id) ON DELETE SET NULL,
    nombre_web VARCHAR(160) NOT NULL,
    descripcion_web TEXT,
    fuente_url TEXT,
    estado estado_propuesta_enum NOT NULL DEFAULT 'pendiente_revision'
);

-- 17. gym_maquina (Inventario real de cada gym sin duplicados)
CREATE TABLE IF NOT EXISTS gym_maquina (
    id SERIAL PRIMARY KEY,
    gym_id INT NOT NULL REFERENCES gym(id) ON DELETE CASCADE,
    maquina_id INT REFERENCES maquina_catalogo(id) ON DELETE RESTRICT,
    maquina_propuesta_id INT REFERENCES maquina_propuesta(id) ON DELETE SET NULL,
    foto_id INT REFERENCES foto_maquina(id) ON DELETE SET NULL,
    estado estado_gym_maquina_enum NOT NULL DEFAULT 'disponible',
    agregada_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Debe apuntar a una máquina del catálogo o a una máquina propuesta
    CONSTRAINT chk_origen_maquina CHECK (
        (maquina_id IS NOT NULL AND maquina_propuesta_id IS NULL) OR
        (maquina_id IS NULL AND maquina_propuesta_id IS NOT NULL)
    ),
    -- Evitar duplicados de la misma máquina del catálogo en el mismo gym (PG-12)
    UNIQUE (gym_id, maquina_id)
);


-- =============================================================================
-- GRUPO 4: PLAN SEMANAL (IA + REGLAS — 3 TABLAS)
-- =============================================================================

-- 18. rutina (Versionada; no se sobrescribe)
CREATE TABLE IF NOT EXISTS rutina (
    id SERIAL PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    rutina_anterior_id INT REFERENCES rutina(id) ON DELETE SET NULL,
    version SMALLINT NOT NULL DEFAULT 1,
    estado estado_rutina_enum NOT NULL DEFAULT 'activa',
    explicacion TEXT,
    motivo_cambio TEXT,
    creada_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 19. rutina_dia
CREATE TABLE IF NOT EXISTS rutina_dia (
    id SERIAL PRIMARY KEY,
    rutina_id INT NOT NULL REFERENCES rutina(id) ON DELETE CASCADE,
    dia_semana dia_semana_enum NOT NULL,
    enfoque VARCHAR(60) NOT NULL,
    UNIQUE (rutina_id, dia_semana)
);

-- 20. rutina_ejercicio (Guarda el ejercicio abstracto, no depende del gym)
CREATE TABLE IF NOT EXISTS rutina_ejercicio (
    id SERIAL PRIMARY KEY,
    rutina_dia_id INT NOT NULL REFERENCES rutina_dia(id) ON DELETE CASCADE,
    ejercicio_id INT NOT NULL REFERENCES ejercicio(id) ON DELETE RESTRICT,
    orden SMALLINT NOT NULL,
    series SMALLINT NOT NULL,
    reps_min SMALLINT NOT NULL,
    reps_max SMALLINT NOT NULL,
    descanso_seg SMALLINT NOT NULL DEFAULT 120
);


-- =============================================================================
-- GRUPO 5: SESIÓN EN VIVO E HISTORIAL (3 TABLAS)
-- =============================================================================

-- 21. sesion_entreno
CREATE TABLE IF NOT EXISTS sesion_entreno (
    id SERIAL PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    gym_id INT REFERENCES gym(id) ON DELETE SET NULL,
    rutina_dia_id INT REFERENCES rutina_dia(id) ON DELETE SET NULL,
    inicio_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fin_at TIMESTAMP,
    duracion_estimada_seg INT,
    estado estado_sesion_enum NOT NULL DEFAULT 'en_curso',
    cuenta_asistencia BOOLEAN NOT NULL DEFAULT FALSE
);

-- 22. sesion_ejercicio (Adaptado al gym del día y reemplazos en vivo)
CREATE TABLE IF NOT EXISTS sesion_ejercicio (
    id SERIAL PRIMARY KEY,
    sesion_id INT NOT NULL REFERENCES sesion_entreno(id) ON DELETE CASCADE,
    rutina_ejercicio_id INT REFERENCES rutina_ejercicio(id) ON DELETE SET NULL,
    ejercicio_id INT NOT NULL REFERENCES ejercicio(id) ON DELETE RESTRICT,
    gym_maquina_id INT REFERENCES gym_maquina(id) ON DELETE SET NULL,
    orden SMALLINT NOT NULL,
    descanso_seg SMALLINT NOT NULL DEFAULT 120,
    motivo motivo_ejercicio_sesion_enum NOT NULL DEFAULT 'plan_original'
);

-- 23. serie_registrada
CREATE TABLE IF NOT EXISTS serie_registrada (
    id SERIAL PRIMARY KEY,
    sesion_ejercicio_id INT NOT NULL REFERENCES sesion_ejercicio(id) ON DELETE CASCADE,
    numero_serie SMALLINT NOT NULL,
    peso_kg NUMERIC(5,1) NOT NULL DEFAULT 0,
    repeticiones SMALLINT NOT NULL,
    es_record BOOLEAN NOT NULL DEFAULT FALSE,
    completada_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- DATOS SEMILLA INICIALES PARA PROBAR CONSULTAS
-- =============================================================================
INSERT INTO grupo_muscular (nombre, region) VALUES
    ('Pecho', 'tren_superior'),
    ('Espalda', 'tren_superior'),
    ('Hombros', 'tren_superior'),
    ('Bíceps', 'tren_superior'),
    ('Tríceps', 'tren_superior'),
    ('Cuádriceps', 'tren_inferior'),
    ('Isquiotibiales', 'tren_inferior'),
    ('Glúteos', 'tren_inferior'),
    ('Pantorrillas', 'tren_inferior'),
    ('Core / Abdomen', 'core')
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO zona_lesion (nombre) VALUES
    ('Rodilla'),
    ('Zona lumbar / Espalda baja'),
    ('Hombro / Manguito rotador'),
    ('Muñeca'),
    ('Codo'),
    ('Tobillo'),
    ('Cervical / Cuello'),
    ('Cadera')
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO maquina_catalogo (codigo, nombre, alias, tipo, descripcion) VALUES
    ('HACK_SQUAT', 'Máquina Hack Squat', ARRAY['Sentadilla Hack', 'Carro Hack'], 'palanca_disco', 'Máquina guiada inclinada para sentadilla con respaldo lumbar.'),
    ('PRENSA_45', 'Prensa de piernas 45°', ARRAY['Leg Press', 'Prensa inclinada'], 'palanca_disco', 'Prensa inclinada a 45 grados para empuje de tren inferior.'),
    ('POLEA_ALTA', 'Polea alta / Jalón dorsal', ARRAY['Lat Pulldown', 'Dorsalera'], 'polea', 'Estación de polea alta con rodillos de sujeción para muslos.'),
    ('REMO_POLEA_BAJA', 'Remo en polea baja sentado', ARRAY['Seated Cable Row', 'Remo sentado'], 'polea', 'Polea baja con apoyo para pies y banco horizontal.'),
    ('PRESS_PECHO_MAQ', 'Press de pecho sentado en máquina', ARRAY['Chest Press', 'Máquina pectoral'], 'selectorizada', 'Empuje horizontal sentado con pila de placas.'),
    ('EXTENSION_CUADRICEPS', 'Camilla de extensión de cuádriceps', ARRAY['Leg Extension', 'Sillón de cuádriceps'], 'selectorizada', 'Extensión de rodilla sentado para aislar cuádriceps.'),
    ('CURL_FEMORAL', 'Camilla de curl femoral', ARRAY['Leg Curl', 'Isquios en camilla'], 'selectorizada', 'Flexión de rodilla para trabajo de isquiotibiales.'),
    ('MANCUERNAS', 'Mancuernas libres', ARRAY['Dumbbells', 'Pesas libres'], 'implemento', 'Par de mancuernas de peso libre.'),
    ('BARRA_OLIMPICA', 'Barra recta / olímpica', ARRAY['Barbell', 'Barra libre'], 'implemento', 'Barra recta para ejercicios compuestos.'),
    ('BANCO_AJUSTABLE', 'Banco plano / inclinable', ARRAY['Flat/Incline Bench'], 'banco_soporte', 'Banco regulable para ejercicios con mancuernas o barra.')
ON CONFLICT (codigo) DO NOTHING;
