# AGENTS.md — Pulse Gym

> Instrucciones para agentes de programación (incluido Codex) que trabajen en este repositorio.
> Objetivo: mejorar legibilidad, mantenibilidad, seguridad y capacidad de prueba **sin cambiar el comportamiento existente por accidente**.

## 1. Alcance y fuentes de verdad

- Este archivo se aplica a todo el repositorio, salvo que un `AGENTS.md` más específico establezca reglas locales compatibles.
- **El código y las pruebas vigentes son la fuente de verdad del comportamiento implementado**; el README y este archivo pueden estar desactualizados. Verifica antes de asumir.
- Arquitectura observada en una auditoría anterior (no necesariamente actual): frontend React + TypeScript + Vite; backend Python + FastAPI + SQLAlchemy; catálogo JSON y configuración opcional de PostgreSQL con Docker Compose.
- No asumir que existen carpetas o herramientas aún no verificadas. No crear nuevas capas, dependencias o patrones por estética.
- Si una instrucción entra en conflicto con las exigencias explícitas del usuario, explicar el conflicto antes de cambiar el alcance.

## 2. Reglas de operación y seguridad

1. **Antes de modificar:** identificar archivos afectados, flujos dependientes, riesgos y una estrategia de verificación. Explicar el alcance brevemente.
2. **Cambios pequeños y relacionados:** no mezclar limpieza estética, nuevas funcionalidades y cambios de contratos en un mismo paso.
3. **No ejecutar comandos, instalar paquetes, lanzar servidores, aplicar migraciones, borrar datos ni modificar archivos sin autorización expresa del usuario para esa operación.** Leer archivos de código solo cuando esté autorizado. Ante una restricción de solo lectura, respetarla.
4. **No abrir, imprimir, copiar, registrar ni modificar archivos `.env`, secretos, claves, tokens, credenciales o datos personales**. Si son necesarios, pedir valores de ejemplo no sensibles o consultar solo nombres de variables documentados.
5. No hacer `commit`, `push`, `merge`, `rebase`, cambios de rama ni abrir PR automáticamente. Solicitar autorización.
6. No modificar archivos generados, dependencias instaladas, builds, bases de datos locales, uploads o datos de usuarios salvo petición explícita.
7. Evitar cambios masivos de formato sin valor funcional. Respetar el estilo establecido mientras se acuerda una convención uniforme.
8. Ante dudas sobre el comportamiento, **preguntar o documentar la incertidumbre**; no inventar reglas de negocio.

## 3. Arquitectura actual y criterio de evolución

### Frontend (estructura observada anteriormente)

- `frontend/src/main.tsx`: entrada y montaje de React.
- `frontend/src/App.tsx`: composición y navegación principales.
- `frontend/src/pages/`: pantallas y ensamblaje de funcionalidades.
- `frontend/src/features/`: lógica y componentes propios de una funcionalidad; actualmente se observó `auth/`.
- `frontend/src/components/`: componentes visuales reutilizables.
- `frontend/src/layouts/`: estructuras de página.
- `frontend/src/lib/`: HTTP, endpoints, tipos y utilidades compartidas.

**Dirección de evolución:** adoptar organización por funcionalidades **de forma progresiva**, cuando reduzca acoplamiento. No mover todas las páginas a `features/` por decreto.

- Las páginas orquestan datos, navegación y presentación; evitan implementar reglas de negocio extensas.
- Los componentes visuales priorizan props explícitas, responsabilidades acotadas y accesibilidad.
- La lógica determinista de entrenamiento (por ejemplo, sugerencias, normalización y cálculos) va en funciones TypeScript puras y comprobables, idealmente junto a su funcionalidad.
- Los hooks encapsulan coordinación de estado y efectos; no se usan como contenedores arbitrarios de lógica.
- El cliente HTTP centraliza transporte y normalización de errores. Los componentes no duplican llamadas `fetch` o lógica de autenticación.
- Evitar dependencias circulares entre funcionalidades; compartir solo aquello que tenga uso real en varios lugares.

### Backend (estructura observada anteriormente)

- `backend/app/main.py`: composición y arranque de FastAPI.
- `backend/app/api/routes/`: contratos HTTP, validación de entrada y delegación.
- `backend/app/api/deps.py`: dependencias HTTP compartidas, incluida autenticación.
- `backend/app/schemas/`: modelos de entrada/salida y validaciones de API.
- `backend/app/services/`: casos de uso y coordinación de reglas de negocio.
- `backend/app/models/`: entidades de persistencia SQLAlchemy.
- `backend/app/db/`: configuración de conexiones y sesiones.
- `backend/app/core/`: configuración general, errores y seguridad.
- `backend/app/scripts/`: tareas auxiliares y cargas de datos.
- `backend/tests/`: pruebas.

**Reglas de dependencia:**

- Ruta HTTP → servicio → persistencia/integraciones, según la necesidad actual.
- Las rutas no deberían contener consultas complejas ni reglas de entrenamiento; delegan en servicios o funciones de dominio.
- Los servicios no deberían importar rutas ni depender de objetos HTTP cuando no sea necesario.
- Los esquemas de API no reemplazan los modelos de base de datos; evitar exponer modelos ORM directamente como contrato público.
- Encapsular proveedores externos (incluida IA) detrás de funciones o adaptadores comprobables cuando simplifique pruebas y sustitución.
- Añadir `repositories/`, `integrations/` u otras capas **solo si existe una necesidad demostrable**. No implementar Clean Architecture ceremonial ni interfaces de un solo uso sin beneficio.
- Mantener límites claros de transacciones (`commit`, `rollback`) y documentar quién es responsable de cada operación.

## 4. Convenciones de Python y FastAPI

- Seguir PEP 8 y las convenciones verificadas del proyecto; priorizar el formatter/linter ya configurado. Si no hay herramientas configuradas, **proponer** Ruff antes de instalarlo.
- Nombres: módulos, funciones y variables en `snake_case`; clases en `PascalCase`; constantes en `UPPER_SNAKE_CASE`.
- Usar anotaciones de tipos en interfaces y funciones nuevas o modificadas cuando aporten claridad. Evitar `Any` innecesario.
- Preferir funciones cortas con nombres que describan la intención; dividirlas cuando haya responsabilidades distintas, no por un número arbitrario de líneas.
- Evitar argumentos mutables como valores predeterminados, imports con `*`, código muerto, `except Exception` silencioso y efectos secundarios durante imports.
- Validar y normalizar entradas en los límites del sistema; no confiar en el frontend como barrera de seguridad.
- Utilizar las dependencias de FastAPI y la gestión de sesiones SQLAlchemy ya establecidas; no abrir sesiones globales improvisadas.
- Los errores HTTP deben usar códigos y cuerpos consistentes; no incluir trazas o secretos en respuestas públicas.
- Considerar idempotencia y transacciones para operaciones que escriben datos.

## 5. Convenciones de TypeScript y React

- Preferir TypeScript estricto según la configuración existente; no introducir `any` para silenciar errores. Usar `unknown` con refinamiento de tipo cuando el dato externo sea incierto.
- Nombres: componentes y tipos/clases en `PascalCase`; funciones, hooks y variables en `camelCase`; hooks con prefijo `use`.
- Respetar nombres de archivos y rutas existentes hasta acordar una migración; evitar renombrados masivos que rompan imports o enlaces.
- Preferir componentes funcionales; mantener hooks en el nivel superior y dependencias de efectos correctas.
- No duplicar estado derivable; derivar valores desde props/estado cuando sea suficiente.
- No introducir optimizaciones prematuras (`useMemo`, `useCallback`, etc.) sin una razón concreta.
- Reducir lógica compleja en JSX: extraer cálculos puros o componentes con responsabilidad clara.
- Mantener accesibilidad básica: etiquetas, estados de error, navegación por teclado y elementos semánticos.
- Centralizar solicitudes HTTP, estados de error y tipos de respuesta acordados; no suponer que todas las respuestas de error son JSON.
- Respetar ESLint/Prettier si ya están configurados. Si no lo están, proponer configuración separadamente, sin instalar ni reformatear todo el proyecto por cuenta propia.

## 6. Reglas de negocio: fuente de verdad y consistencia

- **El backend es la autoridad para validación, autorización y persistencia.** Las validaciones frontend mejoran la experiencia, pero no sustituyen las del servidor.
- Cualquier cambio en límites de series, peso, repeticiones o redondeos exige revisar esquema, servicio, interfaz y pruebas de contrato.
- No alterar las sugerencias de entrenamiento, la prioridad de series previas, las marcas personales o los datos almacenados sin un requisito explícito.
- Las reglas de negocio existentes deben quedar protegidas con pruebas antes de extraerlas o moverlas.
- No cambiar contratos HTTP (rutas, métodos, campos, códigos de estado o formato de errores) sin identificar y actualizar todos los consumidores.

## 7. Persistencia y migraciones

- Una auditoría anterior observó `Base.metadata.create_all(engine)` durante el arranque de FastAPI. **Verificar si aún existe**.
- `create_all` no sustituye las migraciones de esquemas existentes. Si se adopta Alembic, hacerlo como una tarea separada con una estrategia para bases ya pobladas.
- **Nunca ejecutar migraciones sobre bases reales ni eliminar/reescribir datos sin autorización explícita y plan de respaldo y reversión.**
- Probar las migraciones primero sobre una copia representativa; revisar los scripts autogenerados en lugar de aplicarlos ciegamente.
- No cambiar columnas, nulabilidad, índices o relaciones solo para ajustar nombres o estilo.
- Para consultas costosas (por ejemplo, historial por ejercicio), medir consultas y tiempo antes de optimizar. Evitar cambios de semántica o regresiones N+1 al reestructurar.

## 8. Autenticación, errores, PWA e IA

- No afirmar que `logout` revoca tokens del servidor si únicamente elimina la sesión local. Antes de implementarlo, definir si se exige cierre local, revocación individual o de todas las sesiones.
- Evitar fugas de tokens en logs, URL, trazas y mensajes de error.
- Mantener mensajes de error seguros y útiles para el usuario; registrar diagnósticos internos sin datos sensibles.
- No silenciar excepciones de forma indiscriminada, incluidas las del service worker; usar manejo proporcional a la gravedad.
- Las integraciones con IA deben tener entradas/salidas verificables, tratamiento de errores, timeouts y límites razonables, conforme al comportamiento y proveedores existentes.
- Evitar convertir respuestas de IA no verificadas en instrucciones de negocio definitivas o cambios directos en persistencia sin validación.

## 9. Pruebas y comprobación de regresiones

Antes de refactorizar un comportamiento, identificar sus pruebas actuales y añadir las que falten **solo con autorización para cambios**.

Prioridades iniciales sugeridas por la auditoría:

1. Sugerencias de series: registro del día vs. sesión anterior; valores vacíos; confirmación y edición manual.
2. Límites: peso de 0 a 500, repeticiones enteras de 1 a 100, y redondeo a incrementos de 0,5 kg **solo mientras esas reglas sigan confirmadas por el código actual**.
3. Historial aislado por usuario y selección de marcas personales.
4. Registro de series y manejo de transacciones.
5. Autenticación, expiración, cierre de sesión y formatos de error.
6. Migraciones sobre copias de esquemas existentes.

- Pruebas unitarias para funciones puras, integración para persistencia y contratos, y pruebas de interfaz para flujos críticos cuando la infraestructura exista.
- Pruebas atómicas e independientes; cada prueba prepara sus propios datos y no depende del orden de ejecución de otras.
- Antes de sugerir comandos, revisar los scripts y herramientas configurados. **No ejecutar tests, linters, builds ni comandos sin autorización expresa.**
- Si no se ejecutaron verificaciones, informar con precisión: «No ejecutado»; nunca declarar «todo pasa» por inferencia.

## 10. Clean Code: principios pragmáticos

- **SRP:** agrupar código por responsabilidad y motivo de cambio; extraer solo cuando mejore claridad o pruebas.
- **DRY:** evitar duplicación de conocimiento; algunas validaciones deben existir en frontend y backend por seguridad y experiencia.
- **KISS y YAGNI:** preferir la solución más sencilla que cubra la necesidad presente; evitar abstracciones y capas especulativas.
- **SOLID:** aplicar cuando exista evidencia concreta de acoplamiento o extensibilidad problemática, no como checklist mecánico.
- Priorizar legibilidad, nombres precisos, comportamiento explícito y manejo consistente de errores sobre patrones sofisticados.
- Los comentarios explican decisiones y motivos, no repiten lo que ya dice el código.

## 11. Procedimiento obligatorio para cada tarea

**Antes:**
1. Resumir objetivo, alcance, archivos implicados y riesgos.
2. Distinguir problemas confirmados de hipótesis.
3. Proponer el cambio mínimo y cómo comprobar que mantiene el comportamiento.
4. Solicitar autorización cuando corresponda para leer archivos, ejecutar comandos o editar.

**Durante (solo si se autorizó la edición):**
1. Modificar únicamente los archivos necesarios.
2. Mantener contratos y reglas de negocio existentes salvo indicación explícita.
3. Añadir o ajustar pruebas del comportamiento afectado cuando esté dentro del alcance autorizado.
4. No aprovechar la tarea para limpiar partes no relacionadas.

**Después:**
1. Enumerar archivos modificados y por qué.
2. Informar exactamente qué verificaciones se ejecutaron y sus resultados, o cuáles quedaron sin ejecutar.
3. Señalar riesgos residuales, cambios contractuales y pasos que requieran aprobación.
4. No realizar commits ni desplegar sin permiso.

## 12. Primeras tareas sugeridas (no ejecutar automáticamente)

1. Confirmar el estado actual del árbol y dependencias (la auditoría disponible corresponde a una revisión previa).
2. Identificar pruebas vigentes para la sesión de entrenamiento y cubrir reglas críticas.
3. Extraer funciones puras de sugerencia de series desde `frontend/src/pages/Sesion.tsx`, sin modificar el comportamiento.
4. Diseñar migraciones versionadas para el backend y probarlas con respaldo y copia de base existente.
5. Revisar contrato de errores, política de logout y costo de consultas de historial.
6. Actualizar el README conforme a la estructura **verificada**, no según cifras antiguas.

---

**Criterio de éxito:** cambios pequeños, justificados y comprobables; código más claro y seguro, sin nuevas capas innecesarias ni regresiones no detectadas.
