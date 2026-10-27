# PULSE GYM V2 — ESPECIFICACIÓN Y SCRIPT DE DISEÑO FRONTEND PARA FIGMA (MOBILE-FIRST PWA)

> **Propósito de este documento:** Este script sirve como guía maestra para diseñar en **Figma** (manualmente o pegándolo en **Figma AI / First Draft / Lovable / v0**) todas las pantallas del nuevo enfoque **Pulse Gym v2**. Conserva el ADN visual de la versión 1 pero elimina todo el panel administrativo de gimnasio y se enfoca 100% en la **App Móvil del Usuario (un único rol)** con los **8 módulos y 51 requerimientos (PG-01 a PG-51)**.

---

## 1. CONCEPTO DEL PRODUCTO Y REGLAS DE DISEÑO

* **Producto:** Pulse Gym v2 — Tu entrenador personal con IA que conoce las máquinas reales de tu gimnasio.
* **Único Rol:** La persona que entrena (`usuario`). **No existe** panel administrativo, ni sidebar de escritorio, ni cobro de membresías, ni recepción.
* **Formato y Viewport:**
  * **Diseño Mobile-First (PWA Instalable):** Ancho de frame en Figma: **390 × 844 px** (iPhone 14/15/16 base) o contenedor centrado de máx. **430 px** en pantallas grandes.
  * **Navegación Inferior Fija (Bottom Tab Bar):** Altura `64px`, fondo blanco `#FFFFFF`, borde superior `#DCE6DE`, con **5 pestañas principales**:
    1. **Hoy** (Icono: `Home` / `Zap`) — Selección de gym actual + entrenamiento del día adaptado.
    2. **Plan** (Icono: `Calendar` / `List`) — Plan semanal por días + explicación de la IA + versiones.
    3. **Mis Gyms** (Icono: `Dumbbell` / `Camera`) — Inventario de máquinas por gym + Cámara IA + implementos.
    4. **Progreso** (Icono: `Activity` / `TrendingUp`) — Racha, asistencia, récords personales, gráficos y mediciones.
    5. **Perfil** (Icono: `User` / `Shield`) — Composición corporal, objetivos, lesiones activas y descanso por defecto.
  * *Nota:* Durante la **Sesión en Vivo** y el **Visor de Cámara IA**, la barra inferior se oculta para dar foco completo a la tarea y evitar toques accidentales.

---

## 2. SISTEMA DE DISEÑO (DESIGN TOKENS — SE MANTIENE DE V1)

### 2.1 Paleta de Colores Exacta
| Token CSS | Hex | Uso en Figma |
| :--- | :--- | :--- |
| `--primary` | `#16A34A` | Botones primarios, serie completada (`✓`), máquina disponible, éxito |
| `--primary-dark` | `#15803D` | Texto e iconos sobre fondos verde claro |
| `--primary-tint` | `#DCFCE7` | Fondo de badges positivos, serie activa, selección de opción IA |
| `--neon` | `#B6FF45` | **Acento de marca Pulse**, etiquetas de IA, cronómetro activo, récords (`PR`), foco de cámara |
| `--sidebar` / `--dark-1` | `#0A120D` | Headers móviles oscuros, tarjetas de IA, barra de estadísticas en vivo |
| `--black-2` | `#101A14` | Degradados oscuros secundarios y barras de métricas |
| `--ink` | `#0B1410` | Texto principal sobre fondos claros |
| `--muted` | `#5F6F66` | Texto secundario, etiquetas de formularios |
| `--muted-2` | `#8A968D` | Placeholders, pesos/reps sugeridos de la sesión anterior |
| `--surface` | `#FFFFFF` | Fondo de tarjetas y modales (Bottom Sheets) |
| `--bg` | `#F4F7F4` | Fondo general de las pantallas |
| `--border` | `#DCE6DE` | Bordes de tarjetas (`1px solid`) e inputs (`1.5px solid`) |
| `--danger` | `#DC2626` | Botón "Finalizar", alerta de lesión activa, "Máquina ocupada", "Me molesta" |
| `--danger-tint` | `#FEE2E2` | Fondo de alertas de lesión o máquina fuera de servicio |
| `--warning` | `#B45309` | Confianza media de IA, sesión parcial, ejercicio "con precaución" |
| `--warning-tint` | `#FEF3C7` | Fondo de avisos de consentimiento, reintroducción gradual |

### 2.2 Tipografía
* **Títulos, números, cronómetro, pesos (kg), botones y badges:** **`Sora`** (`SemiBold 600`, `Bold 700`, `ExtraBold 800`).
* **Cuerpo de texto, instrucciones de ejercicios, explicaciones de IA e inputs:** **`Manrope`** (`Regular 400`, `Medium 500`, `SemiBold 600`, `Bold 700`).

### 2.3 Componentes Base (Auto Layout en Figma)
* **Tarjetas (`Card`):** Fondo `#FFFFFF`, borde `1px #DCE6DE`, radio `14px`, padding `16px`, sombra sutil `0 1px 4px rgba(0,0,0,0.06)`.
* **Inputs táctiles (pensados para usar con una mano en el gym):** Altura mínima `44px` (`38px` en celdas de serie), radio `8px–10px`.
* **Botones principales:** Altura `48px–50px`, radio `10px`, fuente `Sora Bold 14–15px`.
* **Modales Móviles (`Bottom Sheet`):** Hojas deslizables desde abajo con radio superior `20px` y tirador gris (`40x4px`) para "Elegir Gym", "Máquina Ocupada (Plan B)" y "Me molesta".

---

## 3. MAPA COMPLETO DE MÓDULOS Y PANTALLAS PARA DISEÑAR EN FIGMA

Diseñar los siguientes **6 flujos / módulos (16 pantallas móviles en total, 390×844 px)**:

---

### MÓDULO A: AUTENTICACIÓN, CONSENTIMIENTO Y ONBOARDING FÍSICO (PG-01 a PG-05, PG-19)

#### Pantalla A1 — Login Móvil (`PG-01`)
* **Cabecera oscura (`260px`, `#0A120D`):** Imagen de entrenamiento con degradado oscuro, logo **Pulse** (blanco) **Gym** (`#B6FF45`), titular *"Tu entrenador personal con IA que conoce tu gym"*.
* **Hoja inferior blanca:**
  * Inputs de Correo y Contraseña (`48px` alto) + "Recordarme" y "¿Olvidaste tu contraseña?".
  * Botón primario verde `#16A34A`: **"Iniciar sesión"** + botón secundario **"Continuar con Google"**.
  * Enlace inferior: *"¿No tienes cuenta? Crear cuenta"*.

#### Pantalla A2 — Registro + Consentimiento de Datos Sensibles (`PG-01`, `PG-05`)
* **Header compacto:** *"Crea tu cuenta · Paso 1 de 2"*.
* **Bloque 1 (Cuenta):** Nombre,Correo electrónico, Contraseña y Confirmar contraseña.
* **Bloque 2 (Consentimiento Obligatorio `PG-05`):** Tarjeta ámbar (`#FEF3C7` / borde `#FDE68A`) con checkbox:
  * *"Autorizo a Pulse Gym a guardar mis medidas corporales, lesiones y fotos de máquinas para personalizar mi entrenamiento. Puedo eliminar mi cuenta y mis datos cuando quiera."*
  * Aviso de privacidad de cámara (`PG-48`): *"Al fotografiar máquinas en tu gym, encuadra solo el equipo sin incluir a otras personas."*
* **CTA:** **"Aceptar y continuar al perfil físico →"**.

#### Pantalla A3 — Onboarding Paso 2: Mi Cuerpo, Objetivos y Lesiones (`PG-02`, `PG-03`, `PG-19`)
* **Header:** *"Configura tu cuerpo · Paso 2 de 2"* con barra de progreso al 100%.
* **Sección 1 — Datos físicos y composición corporal (`PG-02`):**
  * Fecha de nacimiento, Sexo (chips), Altura (`cm`) y Peso actual (`kg`).
  * **Badge automático de IMC:** *"IMC calculado: 22.4 (Referencia)"* (no editable).
  * **Campos opcionales (con etiqueta `Opcional`):** `% de Grasa corporal` y `Masa muscular (kg)`. Microcopy: *"Si no los conoces, la IA trabajará con tu peso y altura"*.
* **Sección 2 — Objetivos con prioridad (`PG-03`) y Disponibilidad:**
  * Chips seleccionables con orden de prioridad (`1° Principal`, `2° Secundario`): *Bajar grasa*, *Ganar masa muscular*, *Ganar fuerza*, *Acondicionamiento*, *Salud general*.
  * Nivel: *Principiante*, *Intermedio*, *Avanzado*.
  * Selector de **Días por semana** (`2` a `6` días) y **Minutos por sesión** (`30`, `45`, `60`, `90` min).
* **Sección 3 — Lesiones o molestias actuales (`PG-19`):**
  * Toggle *"¿Tienes alguna lesión o molestia al entrenar?"*.
  * Si está activo: Selector de **Zona** (*Rodilla, Zona lumbar, Hombro, Muñeca, Codo, Tobillo*), **Tipo** (*Aguda / Crónica*), **Estado** (*Activa / En reintroducción*) y switch *"¿Duele al levantar carga?"*.
* **CTA Principal:** **"Guardar perfil y armar mi gym"**.

---

### MÓDULO B: MIS GYMS Y RECONOCIMIENTO DE MÁQUINAS CON IA (PG-06 a PG-14)

#### Pantalla B1 — Mis Gyms e Inventario (`PG-06`, `PG-12`, `PG-13`, `PG-14`)
* **Header (`#0A120D`):** Título *"Mis Gyms"* + botón `+ Nuevo Gym`.
* **Selector de Gym Activo (Tabs o Cards horizontales):**
  * Ej. *"Gym Zona Norte (Último usado)"* · *"Gym Edificio"* · *"Casa"*.
* **Sección 1 — Implementos rápidos y Peso Corporal (`PG-14`):**
  * Chips activables con un toque (sin tomar foto): `✓ Mancuernas`, `✓ Barras y discos`, `✓ Banco ajustable`, `✓ Barra de dominadas`, `✓ Calistenia / Peso corporal (siempre activo)`.
* **Sección 2 — Máquinas fotografiadas en este gym (`gym_maquina`):**
  * Buscador + Contador: *"12 máquinas registradas · Sin duplicados"*.
  * Lista de tarjetas de máquina con miniatura de la foto tomada por el usuario, nombre oficial, grupo muscular y **Selector de Estado Operativo (`PG-13`)**:
    * Badge verde `● Disponible` | Badge ámbar `● Malograda (temporal)` | Badge gris `● Retirada`.
* **Botón Flotante Destacado (`#B6FF45` texto `#0A120D`):** **`+ Fotografiar máquinas (Modo recorrido)`**.

#### Pantalla B2 — Cámara en Modo Recorrido (`PG-07`, `PG-48`)
* **Fondo negro a pantalla completa:**
  * Visor de cámara con 4 esquinas de encuadre en verde neón (`#B6FF45`).
  * Banner superior semitransparente (`PG-48`): *"Encuadra solo la máquina · Evita fotografiar personas"*.
  * Carrete inferior izquierdo con miniaturas de las fotos tomadas en el recorrido (`3 fotos en cola`) para tomar varias seguidas sin frenar.
  * Controles inferiores: Botón **Galería**, **Disparador central blanco (72px)**, y botón **"Analizar fotos (3) →"**.

#### Pantalla B3 — Confirmación de IA: Confianza Alta vs. Elegir entre Parecidas (`PG-08`, `PG-09`, `PG-12`)
* Mostrar las **2 variantes de estado** en Figma:
  * **Estado 1 — Confianza Alta ($\ge 85\%$):**
    * Foto tomada arriba + Tarjeta oscura `#0A120D` con badge neón **`94% CONFIANZA · RECONOCIDA`**: *"Prensa de piernas 45° (Piernas — Cuádriceps / Glúteos)"*.
    * Aviso si ya existe en el gym (`PG-12`): *"Esta máquina ya está en tu inventario. ¿Deseas actualizar su foto?"*.
    * Botones: **"Confirmar y agregar al gym"** (verde) y *"No es esta máquina"*.
  * **Estado 2 — Confianza Media/Baja ($< 85\%$, ej. $62\%$):**
    * Título: *"No estamos 100% seguros. ¿Cuál de estas máquinas tienes enfrente?"*.
    * Lista de **3 tarjetas comparativas** mostrando la **Foto de Referencia del Catálogo (`maquina_foto_ref`)**, nombre y porcentaje:
      1. *Máquina Hack Squat* (`62%`) — Foto de referencia clara.
      2. *Prensa de piernas 45°* (`31%`) — Foto de referencia clara.
      3. *Sentadilla en Multipower / Smith* (`4%`) — Foto de referencia clara.
    * Botón al final de la lista: **"🔍 Ninguna es — Buscar esta máquina en internet"** (`PG-10`).

#### Pantalla B4 — Búsqueda en Internet y Máquina Propuesta (`PG-10`, `PG-11`)
* **Tarjeta de hallazgo web:** Badge **`HALLADA EN INTERNET · MÁQUINA PROPUESTA`**.
* Muestra:
  * **Nombre encontrado:** *"Péndulo Squat (Sentadilla Pendular)"*.
  * **Para qué sirve:** *"Variante guiada de sentadilla con contrapeso que enfatiza cuádriceps reduciendo la carga axial lumbar."*
  * **Músculo que trabaja:** Chip `Cuádriceps / Glúteos` + **Equivalente en catálogo:** *"Similar a: Máquina Hack Squat"*.
  * Nota informativa: *"Ya puedes usarla hoy en tu rutina. Nuestro equipo la revisará para sumarla al catálogo oficial."*
* **CTA:** **"Confirmar y guardar en mi gym"**.

---

### MÓDULO C: PLAN SEMANAL CON REGLAS + IA (PG-20 a PG-27, PG-31 a PG-33)

#### Pantalla C1 — Mi Plan Semanal ("La Receta") (`PG-23`, `PG-24`, `PG-25`, `PG-27`, `PG-31`)
* **Header (`#0A120D`):**
  * Título *"Mi Plan Semanal"* + Selector de versión **`Versión 2 (Activa)`** con botón *"Historial de versiones"* (`PG-31`).
  * Banner de seguridad activa (`PG-20`): Badge rojo/ámbar *"Escudo de lesión activo: Rodilla derecha (0 ejercicios contraindicados)"*.
* **Tarjeta "Por qué la IA armó este plan para ti" (`PG-27`):**
  * Caja con borde neón suave explicando en lenguaje simple: *"Repartí tus 4 días en Torso/Pierna priorizando pérdida de grasa y cuidando tu rodilla derecha: sustituí sentadilla libre y extensión de cuádriceps por bisagras de cadera y prensa con rango controlado."*
* **Tabs de Días de la Semana (`PG-24`):**
  * `Lun · Pecho/Espalda` | `Mar · Pierna (Segura)` | `Jue · Hombro/Brazos` | `Vie · Glúteo/Core`.
* **Lista de Ejercicios del Día Seleccionado (`rutina_ejercicio` — `PG-25`):**
  * Cada tarjeta muestra: Orden (`1`), Nombre del ejercicio, Músculo principal, **Series × Rango de Reps** (ej. `4 series × 8–10 reps`), **Descanso recomendado** (`2:30 min`) y botón *"Cambiar ejercicio"* (cambio parcial sin rehacer todo el plan, `PG-31`).
* **Banner de Revisión Periódica (`PG-33`):** *"Llevas 6 semanas con este plan · [Actualizar según mi progreso]"*.

---

### MÓDULO D: INICIO ("HOY") Y ADAPTACIÓN DIARIA POR GYM (PG-28, PG-32)

#### Pantalla D1 — Home "Hoy" + Selección de Gym (`PG-28`, `PG-32`)
* **Header Superior (`#0A120D`):**
  * Saludo *"Hola, Daniela"* + Avatar + **Selector rápido "¿En qué gym estás hoy?" (`PG-28`):**
    * Pill interactivo destacado: **`📍 Gym Zona Norte (Cambiar ▾)`**.
* **Tarjeta Hero "Tu sesión de hoy (Adaptada a Gym Zona Norte)":**
  * Etiqueta neón: **`MARTES · PIERNA Y GLÚTEO · 100% DISPONIBLE EN ESTE GYM`**.
  * Si una máquina del plan no existe o está averiada en ese gym, muestra aviso automático: *"Adaptamos 1 ejercicio porque este gym no tiene Camilla Femoral → usarás Peso Muerto Rumano con Mancuernas"*.
  * Resumen: `5 ejercicios · ~50 min estimados`.
  * Toggle rápido (`PG-32`): **`⚡ Tengo poco tiempo hoy (Versión corta: 35 min · 4 básicos)`**.
  * **CTA Principal (`#B6FF45` texto `#0A120D`):** **`▶ Iniciar rutina de hoy`**.
* **Fila de Estadísticas Rápidas (3 KPIs):**
  * **Racha actual:** `5 días 🔥` (`PG-38`).
  * **Asistencia del mes:** `12 sesiones`.
  * **Peso actual:** `58.0 kg (-1.2 kg)`.
* **Acceso secundario:** *"¿Entrenaste ayer y olvidaste anotarlo? [Registrar entrenamiento pasado]"* (`PG-39`).

---

### MÓDULO E: SESIÓN EN VIVO (EL CORAZÓN DE LA APP — PG-22, PG-29, PG-30, PG-34 a PG-37, PG-40)

#### Pantalla E1 — Entrenamiento en Vivo + Cronómetro + Registro de Series (`PG-34`, `PG-35`, `PG-40`)
* **Header Fijo (`#0A120D`):**
  * Indicador `● Sesión congelada y en curso` (`PG-30`) + **Cronómetro general grande en `#B6FF45`: `32:14`** (`PG-34`).
  * Botón rojo a la derecha: **`Finalizar rutina`** (`PG-37`).
* **Barra de Métricas en Vivo (`#101A14`):**
  * `Series: 7 / 16 (44%)` | `Volumen: 2,840 kg` | `Gym Zona Norte`.
* **Tarjeta de Ejercicio Activo (`PG-35`):**
  * Título: **`1. Prensa de piernas 45°`** + Subtítulo: *"Máquina asignada en tu gym · Descanso: 2:00 min"*.
  * **Botones de Acción Rápida en Vivo (2 pills en la esquina superior de la tarjeta):**
    * Botón ámbar/rojo: **`⏳ Máquina ocupada`** (`PG-29`).
    * Botón rojo suave: **`⚠️ Me molesta`** (`PG-22`).
  * **Sugerencia de Sobrecarga Progresiva (`PG-41`):** Pill verde `"📈 Completaste 4×10 la última vez → Hoy intenta 72.5 kg"`.
  * **Tabla de Series (diseñada para usar con el pulgar):**
    * Columnas: `Serie` | `Vez pasada` | `Peso (kg)` | `Reps` | `Listo`.
    * Fila 1 (Completada con Récord `PG-40`): `1` | `70 kg × 10` | **`72.5`** | **`10`** | Botón verde `✓` + Badge **`🏆 ¡NUEVO RÉCORD!`**.
    * Fila 2 (Actual): `2` | `70 kg × 10` | Input `[ 72.5 ]` | Input `[ 10 ]` | Botón circular `✓ Listo`.
    * Fila 3 (Pendiente): `3` | `70 kg × 9` | Placeholder `72.5` | Placeholder `10` | Botón gris `○`.

#### Pantalla E2 — Temporizador Flotante de Descanso con Sonido (`PG-36`)
* **Barra / Modal inferior flotante (`#0A120D` con borde `#B6FF45`):**
  * Se activa inmediatamente al tocar `✓ Listo` en una serie.
  * Muestra barra de progreso circular o lineal con cuenta regresiva grande: **`01:45 / 02:00`** + icono de altavoz `🔊 Sonará al terminar`.
  * Botones rápidos: **`-15s`** | **`+15s`** | **`Saltar descanso`**.

#### Pantalla E3 — Bottom Sheet: "Máquina Ocupada" y "Me Molesta" (`PG-22`, `PG-29`)
* **Variante 1 — Máquina Ocupada (`PG-29`):**
  * Título: *"¿La Prensa 45° está ocupada? Elige tu reemplazo para hoy:"* (Nota: *"Solo cambia la sesión de hoy; tu plan semanal no se altera"*).
  * **Opción 1 (Recomendada — Otra máquina libre de tu gym):** *Máquina Hack Squat* (Disponible en Gym Zona Norte · Mismo músculo).
  * **Opción 2 (Peso libre de tu gym):** *Sentadilla Goblet con Mancuerna* (Sugiere empezar con peso prudente, `PG-41`).
  * **Opción 3 (Calistenia / Sin equipo):** *Sentadilla Búlgara sin equipo*.
* **Variante 2 — Reportar Molestia en Vivo (`PG-22`):**
  * Título: *"¿Qué zona te molesta en este ejercicio?"* $\rightarrow$ Chips: `Rodilla`, `Espalda baja`, `Hombro`, `Otra`.
  * Propone un sustituto inmediato que **no cargue esa zona** + Checkbox *"Guardar esta molestia en mi perfil de lesiones para proteger mis próximas rutinas"*.

#### Pantalla E4 — Resumen al Finalizar y Calificación de la Sesión (`PG-37`, `PG-38`, `PG-39`)
* Mostrar los **2 estados de calificación de la IA (`PG-37`)**:
  * **Caso A — Sesión Completa ($\ge 80\%$ series y tiempo coherente):**
    * Medalla verde/neón **`¡SESIÓN COMPLETA! · +1 DÍA DE RACHA (6 DÍAS 🔥)`** (`PG-38`).
    * Resumen: `Duración: 48 min (Estimado: 50 min)` · `15/16 series (94%)` · `2 Nuevos Récords Personales 🏆`.
  * **Caso B — Sesión Parcial ($< 80\%$ series o tiempo muy corto):**
    * Badge ámbar **`SESIÓN PARCIAL GUARDADA EN TU HISTORIAL`**.
    * Explicación amigable: *"Marcaste 6 de 16 series (18 min). Se guardó todo tu avance en el historial, aunque no suma a la racha."*
    * Botón especial (`PG-39`): **`✏️ Olvidé marcar series — Completar el resto con lo planeado`** (pasa a registro manual).

---

### MÓDULO F: PROGRESO, HISTORIAL, MEDICIONES Y PERFIL (PG-38 a PG-46)

#### Pantalla F1 — Panel de Progreso, Racha y Récords (`PG-38`, `PG-40`, `PG-42`, `PG-43`, `PG-46`)
* **Header (`#0A120D`):** *"Mi Progreso"*.
* **Tarjetas de Constancia (`PG-38`):** Racha actual (`6 días`), Sesiones esta semana (`3/4`), Sesiones este mes (`14`).
* **Alertas Inteligentes de Progresión (`PG-42`, `PG-43`):**
  * Ejemplo de estancamiento (`PG-43`): *"Llevas 3 semanas con 40 kg en Remo en polea. ¿Quieres que ajustemos el rango de repeticiones?"*.
  * Ejemplo de retorno tras ausencia (`PG-42`): *"Volviste después de 2 semanas: hoy redujimos los pesos un 10% para cuidar tus articulaciones."*
* **Gráfico de Evolución:** Selector por ejercicio (*Prensa 45°, Press Pecho*) mostrando la curva de peso máximo y récords personales (`🏆`).
* **Lista de Historial de Sesiones (`PG-46`) + Botón `"Registrar entrenamiento pasado"` (`PG-39`):**
  * Cada fila muestra: Fecha, Nombre del día, Gym donde entrenó, Duración y Badge de estado (`Completa`, `Parcial`, `Manual`).

#### Pantalla F2 — Historial y Registro de Mediciones Físicas (`PG-45`)
* **Gráfico de Composición Corporal:** Curvas de `Peso (kg)`, `% Grasa` y `Masa Muscular (kg)`.
* **Formulario / Modal "+ Nueva Medición":**
  * Fecha, Peso (`kg`), `% Grasa`, `Masa muscular (kg)`, `Cintura (cm)`, `Cadera (cm)`.
  * **Alerta de validación atípica (`PG-45`):** Banner ámbar si el usuario escribe un valor muy distinto al anterior (ej. *"Ingresaste 85 kg y tu última medición fue 58 kg. ¿Es correcto?"*).
  * Recordatorio configurable: *"Próxima medición sugerida en 14 días"*.

#### Pantalla F3 — Perfil del Usuario, Lesiones y Privacidad (`PG-04`, `PG-05`, `PG-19`, `PG-21`, `PG-44`)
* **Datos editables (`PG-04`):** Objetivo, Nivel, Días por semana, Minutos por sesión, **Descanso por defecto** (ej. `120 seg`). Si cambia datos clave, muestra aviso: *"¿Deseas generar una nueva versión de tu plan semanal con estos cambios?"*.
* **Gestor de Lesiones (`PG-19`, `PG-21`):**
  * Lista de lesiones con cambio de estado en un toque: **`Activa (Bloqueo total)`** $\rightarrow$ **`En reintroducción (Carga reducida)`** $\rightarrow$ **`Recuperada`**.
* **Recordatorios y Cuenta (`PG-05`, `PG-44`):**
  * Switch *"Recordarme entrenar si llevo 3 días sin sesiones"* (`PG-44`).
  * Botones de cuenta: *"Cerrar sesión"* y *"Eliminar mi cuenta y todos mis datos sensibles"* (`PG-05`).
