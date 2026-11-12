# AGENTS.md — Pulse Gym V2

> Reglas compartidas para Codex, Claude Code y otros agentes que trabajen en este repositorio.
> Propósito: **implementar tickets nuevos, corregir defectos y refactorizar** con código legible, seguro, probado y sin sobreingeniería.

## 1. Prioridades y fuentes de verdad

1. Cumple el ticket y sus criterios de aceptación, sin agregar funcionalidades no solicitadas.
2. Preserva contratos y comportamientos existentes excepto cuando el ticket autorice explícitamente cambiarlos.
3. Sigue el código, las pruebas y las configuraciones **actuales**, no suposiciones de conversaciones anteriores.
4. Consulta `backend/ARCHITECTURE.md` **si existe** para conocer los flujos, las decisiones y los riesgos vigentes. Si contradice el código, identifica la diferencia; no la resuelvas silenciosamente.
5. Prefiere cambios pequeños, cohesionados y fáciles de revisar. Aplica SRP, DRY, KISS, YAGNI y SOLID con criterio, nunca como excusa para añadir capas.

## 2. Permisos, alcance y datos sensibles

- **Lectura:** puedes inspeccionar código, pruebas y documentación necesaria para la tarea; excluye secretos, datos personales y archivos `.env*`.
- **Ticket de implementación autorizado:** puedes crear o modificar archivos necesarios **dentro del alcance del ticket**, incluidos tests. Antes, comunica brevemente plan, archivos previstos y riesgos; no solicites otra autorización por cada edición ordinaria.
- **Validación:** ejecuta las pruebas, verificaciones de tipos y compilaciones pertinentes cuando el usuario o el modo de trabajo lo permitan. Si se prohíben comandos, no los ejecutes; informa qué queda pendiente. Usa únicamente datos temporales y proveedores simulados.
- **Fuera de alcance:** solicita autorización antes de instalar o actualizar dependencias, aplicar migraciones, tocar datos o servicios reales, cambiar contratos públicos, desplegar, eliminar datos o modificar archivos ajenos al ticket.
- **Git:** no hagas `commit`, `push`, `merge`, `rebase` ni cambios de rama sin autorización explícita. Puedes inspeccionar el diff si las herramientas y permisos lo permiten.
- No abras, muestres, copies ni registres `.env*`, credenciales, claves, tokens, fotografías privadas, bases reales, información personal ni otros secretos. Usa valores sintéticos.
- No aproveches un ticket para reformatear el repositorio completo, renombrar grandes áreas o refactorizar funcionalidades no relacionadas.

## 3. Arquitectura de referencia: conservar lo que funciona

### Backend: Python, FastAPI, Pydantic, SQLAlchemy

- `backend/app/main.py`: composición y arranque de FastAPI.
- `backend/app/api/routes/` y `api/deps.py`: endpoints, autenticación y dependencias HTTP.
- `backend/app/services/`: casos de uso, reglas, coordinación y proveedores externos existentes.
- `backend/app/schemas/`: validación y contratos Pydantic.
- `backend/app/models/`: tablas y relaciones SQLAlchemy.
- `backend/app/db/`: sesiones, motor y carga inicial.
- `backend/app/core/`: configuración, seguridad y utilidades transversales justificadas.
- `backend/tests/`: pruebas aisladas de backend.

Dirección habitual: **ruta → servicio → modelos/DB e integraciones**. Las rutas deben delegar las reglas complejas; los servicios no deben depender de las rutas. Mantén la separación entre ORM y respuesta pública. No crees `repositories/`, `domain/`, adaptadores o interfaces de un solo uso por estética. Un servicio puede coordinar otros servicios cuando eso corresponde a su caso de uso.

### Frontend: React, TypeScript y Vite

- `frontend/src/pages/`: páginas y coordinación visual.
- `frontend/src/features/`: código de funcionalidades cuando la separación aporte valor.
- `frontend/src/components/`: componentes reutilizables de presentación.
- `frontend/src/layouts/`: estructuras de navegación/página.
- `frontend/src/lib/`: HTTP, endpoints, tipos y utilidades compartidas ya existentes.

Mantén la lógica determinista fuera de JSX o componentes de gran responsabilidad: funciones puras cercanas a la funcionalidad. Los hooks coordinan estado y efectos; los componentes presentan e interactúan. No conviertas todo el frontend a `features/` de manera masiva. No dupliques el transporte HTTP.

## 4. Tickets nuevos: proceso de extremo a extremo

**Antes de codificar:**
1. Identifica objetivo, criterios de aceptación, flujos afectados, restricciones y casos límite. Si falta algo no bloqueante, toma una decisión mínima y explícitala; consulta solo las ambigüedades que puedan cambiar materialmente el resultado.
2. Localiza el módulo propietario, patrones existentes, consumidores, pruebas y contratos. **Reutiliza primero** los componentes y utilidades existentes.
3. Define un plan corto: archivos a crear/modificar, responsabilidades, pruebas y posibles cambios de API o BD. Evita crear carpetas nuevas sin necesidad.

**Al implementar:**
1. Implementa primero el camino mínimo completo que cumple el ticket; evita generalizar para requisitos futuros hipotéticos.
2. Ubica cada responsabilidad donde corresponda: ruta/API, servicio/caso de uso, regla pura, persistencia, componente o hook. No mezcles consultas, lógica, formato y UI en una única función si pueden separarse de forma natural.
3. Escribe código comprensible con nombres que expresen intención y funciones cohesionadas; usa abstracciones únicamente cuando reduzcan complejidad real.
4. Añade las pruebas pertinentes y conserva compatibilidad con consumidores existentes. No cambies modelos, migraciones, endpoints, respuestas o reglas de negocio sin necesidad y autorización.

**Al entregar:**
1. Explica qué ticket se implementó y dónde está cada responsabilidad.
2. Enumera archivos creados/modificados, comportamiento, contratos y pruebas reales con sus resultados.
3. Señala limitaciones y verificaciones no ejecutadas; no afirmes que todo funciona sin haberlo probado.
4. Informa decisiones de diseño y riesgos relevantes, sin presentar cambios adicionales no autorizados como hechos.

## 5. Tamaño de archivos y funciones: control de complejidad

**Objetivo: evitar archivos monolíticos, no imponer un máximo rígido de líneas.** El número de líneas es una señal para revisar, nunca una razón suficiente para dividir.

- Como guía orientativa, si un `.py`, `.ts` o `.tsx` **nuevo o modificado** se acerca a ~250–350 líneas de lógica, revisa su cohesión, las responsabilidades y si conviene extraer piezas. No es un límite ni obliga a dividirlo.
- Si una función exige leer muchas ramas, combina consultas, reglas y presentación o tiene un motivo de cambio independiente, considera extraer una **función privada bien nombrada** o una función pura comprobable.
- En React, considera separar un componente o hook cuando tenga identidad funcional, estado/efectos propios o pueda entenderse y probarse de manera independiente.
- **Crea otro archivo** solo si aparece un límite claro de responsabilidad, un consumidor compartido real o una necesidad de pruebas/mantenibilidad; no fragmentes en archivos diminutos para cumplir una cifra.
- Evita los extremos: ni un archivo que haga de todo, ni docenas de módulos con funciones triviales dispersas. Mantén la lógica relacionada cerca de donde se usa.
- No dupliques funciones para reducir imports; tampoco crees utilidades genéricas para un único uso claro.
- No refactorices código preexistente fuera del ticket solo porque supere la guía de líneas.

## 6. Convenciones Python y backend

- PEP 8 y estilo del repositorio. `snake_case` para funciones/variables/módulos; `PascalCase` para clases; `UPPER_SNAKE_CASE` para constantes.
- Añade type hints claros en funciones nuevas o modificadas, especialmente en límites entre módulos. Evita `Any` y `dict` sin estructura cuando un tipo sencillo aporte claridad; no construyas jerarquías de tipos innecesarias.
- Prefiere retornos explícitos, nombres descriptivos, funciones cohesionadas y errores con significado. No uses `except Exception: pass`, mutable defaults ni efectos de inicialización nuevos innecesarios.
- Mantén validaciones de autoridad en backend, autenticación/autorización y manejo consistente de excepciones.
- Documenta **qué función controla `commit`, `flush` y `rollback`** y qué efectos de escritura pueden aparecer en operaciones que parecen consultas.
- Añade dependencias nuevas, formatters, linters o capas solo tras revisar lo existente y obtener autorización si son necesarios.

## 7. Convenciones TypeScript, React y estilos

- Respeta TypeScript `strict`; evita `any` y aserciones de tipo injustificadas. Valida datos externos en el límite correspondiente cuando el contrato lo requiera.
- `PascalCase` para componentes y tipos; `camelCase` para funciones y variables; hooks con prefijo `use`.
- Componentes funcionales con hooks bien usados, estado mínimo, accesibilidad básica y efectos controlados. Evita efectos que mezclen demasiados procesos, JSX con decisiones extensas y optimizaciones prematuras.
- Utiliza el cliente HTTP existente; reutiliza patrones de loading, error y tipos. Conserva estructura visual y contratos salvo requisito del ticket.
- Respeta CSS, nombres de clases, organización y herramientas de formato ya presentes. No introduzcas un sistema visual paralelo en un ticket aislado.

## 8. Reglas actuales de Pulse Gym que no deben romperse

- El backend es autoridad para reglas de series, límites, redondeo, historial, marcas personales, lesiones, planes y persistencia.
- La creación de lesión desde reemplazo de ejercicio y el propio reemplazo comparten una transacción; la creación independiente de lesión conserva su confirmación. No reintroducir commits parciales.
- El cierre de sesiones olvidadas **puede escribir y confirmar cambios** antes de la consulta/reemplazo: revisar este efecto antes de modificar transacciones; no alterarlo silenciosamente.
- La normalización Unicode común está en `backend/app/core/texto.py`; reutilizarla en lugar de duplicarla.
- La selección de IA para adaptación y la combinación de planes están separadas de la coordinación de proveedores. Conservar prioridades, orden, reintentos, fallback y motivos de validación.
- `ErrorIA` usa categorías internas controladas. No volver a persistir textos externos libres donde ya se guardan categorías.
- **Decisión vigente:** conservar los textos públicos actuales de reconocimiento IA, incluso `503 / ia_fallo`; existe un riesgo de exposición conocido y debe documentarse. **No cambiar esos textos sin autorización explícita.**
- El borrado de fotografías ocurre después del commit SQL y registra fallos sanitizados; no es atómico con el sistema de archivos ni garantiza limpiar huérfanos. No registrar rutas, nombres de fotos ni datos personales.
- `create_all` no migra tablas existentes. Tratar las migraciones como proyecto separado con copia de respaldo, estrategia de adopción y autorización.
- El frontend contiene reglas puras de sugerencia de sesiones y pruebas unitarias. No reintroducir cálculos en JSX. La cobertura integral de interfaz y compatibilidad del entorno Node quedaron como tareas separadas.

## 9. Pruebas y criterios de calidad

- **Cada prueba debe ser atómica e independiente**: prepara sus fixtures/datos, verifica un comportamiento y no depende del estado ni orden de otras pruebas.
- En tickets nuevos, añadir al menos las pruebas útiles para los criterios de aceptación y bordes relevantes; en refactorizaciones, caracterizar el comportamiento antes de moverlo cuando exista riesgo.
- Pruebas unitarias para reglas puras, integración para servicios y contratos SQL/HTTP, interacción React para flujos críticos según infraestructura disponible.
- Usar SQLite/almacenamiento temporal y proveedores de IA simulados donde se requiera; no tocar bases reales ni servicios externos en verificaciones de rutina.
- Comprobar pruebas relacionadas y, cuando esté permitido y sea razonable, suite completa, TypeScript y compilación. Reportar lo ejecutado y lo pendiente por separado.
- Revisar diff para detectar cambios ajenos al ticket, dependencias innecesarias, secretos, duplicación, regresiones, archivos excesivamente complejos y contratos afectados.
- No usar el recuento anterior de pruebas como garantía del estado actual; verificar resultados en la ejecución presente.

## 10. Cuándo detenerse y pedir decisión

Solicita decisión explícita antes de: alterar contrato HTTP o texto público, cambiar reglas de entrenamiento, añadir/modificar migraciones o datos existentes, instalar dependencias, introducir integraciones de red reales, implementar cambios extensos fuera del ticket o modificar políticas de privacidad/seguridad aceptadas.

**Criterio de éxito:** un ticket implementado con el menor diseño suficiente; código legible y cohesionado, sin archivos monolíticos evitables, con pruebas independientes, dependencias controladas y comportamiento verificado.
