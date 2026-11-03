# Sprint 4 — Sesión en vivo

Leyenda: ✅ hecho y probado · 🟡 hecho, pero falta algo que no puede resolver el código · ⏭️ depende de otro sprint

> Las tarjetas se tomaron del **Módulo E** de `docs/guia-diseno-figma-pulse-gym-v2.md` (PG-22, PG-29, PG-30,
> PG-34 a PG-37, PG-40). Si en Trello el Sprint 4 tiene otras tarjetas, avísame y lo ajusto.

## Cómo probarlo en 2 minutos
1. Arranca todo como siempre (`INICIAR_PULSE_GYM.bat`, o backend + frontend a mano).
2. Entra con `demo@pulsegym.app` / `Pulse2026!`. Si hoy no es día de tu plan, ve a **Plan** y arma uno que incluya hoy
   (o usa «Adelantar» en **Hoy**).
3. **Hoy** → elige el gym → **▶ Iniciar rutina de hoy**. Se abre la sesión en vivo a pantalla completa.
4. Escribe kilos y repeticiones y toca **✓**: arranca el descanso con su cuenta regresiva y suena al terminar.
5. Prueba **Máquina ocupada** y **Me molesta** en un ejercicio, y al final **Finalizar rutina** para ver el resumen.
6. Si cierras la app en medio de la rutina, **Hoy** muestra «Tienes una rutina en curso» para continuarla.

No usa IA: todo son reglas (rápido, gratis y funciona aunque Gemini esté caído).

## Estado por tarjeta

| Tarjeta | Estado | Qué hay | Qué falta |
|---|---|---|---|
| **PG-30** Sesión congelada | ✅ | Al iniciar se copian los ejercicios ya adaptados al gym (PG-28). Si después cambia el plan, el inventario o las lesiones, la sesión en curso no se toca (prueba automática). Solo una rutina en curso a la vez; se puede continuar después de cerrar la app; «Descartar» si se empezó por error. Una sesión abierta más de 6 h se cierra sola como parcial | — |
| **PG-34** Cronómetro general | ✅ | Grande y siempre visible; se calcula con la hora del **servidor**, así que sigue bien aunque recargues o el reloj del celular esté mal | — |
| **PG-35** Registrar series | ✅ | Tabla para el pulgar: Serie · Vez pasada · Kg · Reps · ✓. Propone el peso de tu serie anterior (o el de la vez pasada) y las reps del plan. Corregir, deshacer y hasta 3 series extra. Repetir el mismo pedido no duplica (sirve con mala señal en el gym). Peso de medio en medio kilo | Funciona **con conexión**: sin señal muestra el error y no pierde lo escrito, pero no guarda en cola |
| **PG-36** Descanso con sonido | 🟡 | Se abre solo al marcar una serie, con el descanso de ese ejercicio: cuenta regresiva, barra de progreso, −15 s, +15 s y Saltar. Al terminar suenan 3 pitidos (Web Audio, sin archivos) | **Probar el sonido en un celular real** (iPhone en modo silencio no suena; es una regla del sistema). Vibración y pantalla bloqueada quedan fuera, como dice PG-47 |
| **PG-29** Máquina ocupada | ✅ | Reemplazos solo para hoy en orden: otra máquina libre de tu gym → peso libre → sin equipo, sin usar la máquina ocupada y siempre seguros con tus lesiones. El plan semanal no cambia (prueba). Si ya hiciste series, se conservan: el ejercicio queda «Reemplazado» con lo hecho y el nuevo sigue con las que faltan | — |
| **PG-22** Me molesta | 🟡 | Eliges la zona y propone ejercicios que no la cargan (la zona se trata como lesión activa). Casilla «Guardar esta molestia en mi perfil de lesiones» (solo si aceptaste el consentimiento): crea la lesión y el próximo plan se regenera solo (PG-20). Muestra el aviso «no reemplaza a un médico» | Depende de las contraindicaciones del catálogo, que siguen **sin revisar por un entrenador** (PG-16) |
| **PG-37** Finalizar y calificar | 🟡 | **Completa** = al menos 80 % de las series y un tiempo coherente (no menos del 40 % del estimado). Si no, **parcial**: se guarda igual en el historial, pero no cuenta para la asistencia. Resumen con duración vs. estimado, series, volumen y récords | La guía dice «calificación de la IA»: la hice con **reglas** (ver decisiones). ⏭️ La racha (PG-38) y «Olvidé marcar series» (PG-39) son del Sprint 5 |
| **PG-40** Récords personales | ✅ | Récord = más peso que tu mejor marca en ese ejercicio, o el mismo peso con más repeticiones (sin peso: más repeticiones). Se marca al instante («🏆 ¡Nuevo récord!») y se recalcula si corriges o borras una serie. Cada ejercicio muestra tu récord actual | ⏭️ El panel de récords y progreso es del Sprint 5 |

## Decisiones que tomé y conviene que confirmes
1. **La calificación (PG-37) es con reglas, no con IA**: es instantánea, gratis y no falla. Los umbrales están en
   `backend/.env`: `SESION_PCT_COMPLETA=0.8`, `SESION_TIEMPO_MIN_PCT=0.4`, `SESION_HORAS_MAX=6`.
2. **La primera vez que haces un ejercicio no hay récord** (no hay con qué comparar). Igualar tu marca tampoco es récord.
3. **Las series extra no suben el porcentaje**: el 80 % se mide sobre las series del plan.
4. **Sesión olvidada**: si queda abierta más de 6 h, se cierra sola como parcial, con la hora de la última serie.
5. **Un reemplazo que cambia el tipo de ejercicio** (de varias articulaciones a una, o al revés) toma las series y
   descansos de reglas para ese tipo (igual que en PG-28).
6. **Pantalla completa sin barra inferior** durante la sesión, para no salir por error en medio de una serie.
7. **Base de datos**: las 3 tablas del diagrama (`sesion_entreno`, `sesion_ejercicio`, `serie_registrada`) con
   campos extra que la app necesita (nombre del gym para el historial si lo borras, día y enfoque, series y reps
   planeadas, a qué reemplaza, nota del cambio, precaución). Se crean solas al arrancar; **no se modificó ninguna
   tabla existente**. Borrar un gym deja `gym_id` en NULL y conserva la sesión (lo que pedía PG-06).

## API nueva
| Método | Ruta | Para qué |
|---|---|---|
| GET | `/api/sesiones/actual` | La rutina en curso (o `null`) |
| POST | `/api/sesiones` | Iniciar `{"gym_id", "dia", "fecha"}` · 409 `sesion_en_curso` |
| GET / DELETE | `/api/sesiones/{id}` | Ver (con resumen si terminó) / descartar una en curso |
| PUT / DELETE | `/api/sesiones/{id}/ejercicios/{se}/series/{n}` | Registrar o corregir / deshacer una serie |
| GET | `/api/sesiones/{id}/ejercicios/{se}/reemplazos?motivo=&zona=` | Opciones para máquina ocupada o molestia |
| POST | `/api/sesiones/{id}/ejercicios/{se}/reemplazar` | Cambiar solo por hoy `{"ejercicio_id", "motivo", "zona", "guardar_lesion"}` |
| POST | `/api/sesiones/{id}/finalizar` | Terminar y calificar |

`GET /api/hoy` ahora incluye `sesion_en_curso_id`.

## Pendiente de la Definición de terminado
- ✅ **Diagrama `.drawio`**: campos nuevos en `sesion_entreno` y `sesion_ejercicio` (ábrelo en diagrams.net y
  acomoda si algo quedó apretado).
- **Revisión por otro integrante** y comentario en cada tarjeta de Trello.

## Probado
- **Backend:** 188 pruebas automáticas pasan (20 nuevas del Sprint 4; las 168 anteriores siguen pasando).
- **App** (navegador a 390 px contra PostgreSQL 16, en una base de prueba aparte): Hoy → elegir gym → iniciar →
  registrar serie (cronómetro, volumen y descanso) → máquina ocupada con una serie hecha → me molesta (espalda baja) →
  finalizar como parcial. Por API contra PostgreSQL: sesión completa con récord y «vez pasada».
- **No probado:** teléfono físico (sonido en iPhone/Android).
