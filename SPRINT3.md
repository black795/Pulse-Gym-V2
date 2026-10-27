# Sprint 3 — Plan semanal y adaptación por gym

Leyenda: ✅ hecho y probado · 🟡 hecho, pero falta algo que no puede resolver el código · ⏭️ depende de otro sprint

## Cómo probarlo en 2 minutos
1. Arranca todo como siempre (`INICIAR_PULSE_GYM.bat`, o backend + frontend a mano).
2. Entra con `demo@pulsegym.app` / `Pulse2026!` → pestaña **Plan** → elige los días → **Armar mi plan**.
3. Mira el escudo de lesión (la cuenta demo tiene la rodilla en recuperación), el «Por qué este plan» y cada día.
4. Pestaña **Hoy** → elige el gym (el último usado viene marcado) → ves el día que toca adaptado a ese gym, con lo
   que cambió y por qué. Si hoy no toca, ofrece adelantar el siguiente día.

Sin clave de IA funciona con la **IA simulada** (usa la propuesta de las reglas): sirve para probar todas las pantallas.

## Cómo funciona (reglas + IA)
```
Perfil, lesiones y gyms ─► REGLAS fijan los límites ─► IA elige, ordena y explica ─► VALIDACIÓN ─► se guarda
                           · días y esquema (PG-24)      (un pedido por día, en       · si falla: se le pide de
                           · grupos de cada día           paralelo, + uno para la       nuevo diciendo por qué
                           · ejercicios permitidos        explicación general)          (máx. 2 reintentos)
                             (equipo y lesiones, PG-20)                               · si sigue fallando o se
                           · series/reps/descanso (PG-25)                               acaba el tiempo: ese día
                                                                                        usa la versión de reglas
```
- La IA **no puede** proponer nada fuera de la lista que le dan las reglas, y de todos modos se revisa todo.
- Las series, repeticiones y descansos los pone el sistema (PG-25); la IA no los escribe. Así su respuesta es corta.
- El plan guardado dice su origen: **IA**, **IA + reglas** (algunos días de reglas) o **Reglas**.
- Cada plan es una **versión** nueva (la anterior queda archivada): base para el historial de versiones (PG-31, Sprint 5).
- La adaptación del día se guarda: si nada cambió (mismo gym, inventario y lesiones) no se vuelve a llamar a la IA.

## Estado por tarjeta

| Tarjeta | Estado | Qué hay | Qué falta |
|---|---|---|---|
| **PG-20** Exclusión de ejercicios incompatibles | ✅ | Regla dura antes de que la IA elija, también en reemplazos y en la adaptación: «evitar» nunca aparece; «precaución» **solo** con la lesión en reintroducción (y sale marcado). El backend revisa el plan final y vuelve a revisar el plan guardado cada vez que se pide. Una lesión nueva (o un cambio de estado) **regenera el plan sola** y no gasta las regeneraciones del usuario. Si un grupo se queda sin ejercicios posibles, se omite y se avisa. Prueba de 20 planes seguidos con rodilla activa: ninguno contraindicado | Las contraindicaciones del catálogo siguen **sin revisar por un entrenador** (PG-16) |
| **PG-23** Plan semanal personalizado | ✅ | Enfoque por día, usa objetivo, nivel, días, minutos, lesiones, % de grasa y masa muscular. El usuario elige **qué días** entrena y el plan tiene exactamente esos. 4 a 8 ejercicios según los minutos. Cada grupo grande al menos 1 vez por semana. Se ve la semana completa y se regenera hasta 3 veces al día. **Nunca pasa de 18 s** | Con la capa gratuita de Gemini, hoy muchas veces sale «IA + reglas» (ver abajo) |
| **PG-24** Estructura según días | 🟡 | 1–3 días: cuerpo completo · 4: torso/pierna · 5+: empuje/tirón/pierna. Nunca el mismo grupo principal en días seguidos (domingo y lunes también cuentan): probado con las 127 combinaciones de días | **Que un entrenador valide los esquemas** antes del lanzamiento |
| **PG-25** Series, repeticiones y descanso | 🟡 | Fuerza 3–5 × 3–6, 2–3 min · Músculo 3–4 × 8–12, 60–90 s · Resistencia 2–3 × 15–20, 30–60 s. Más descanso en los básicos (varias articulaciones). Principiante: máximo 3 series | **Validar los rangos con un entrenador** (la tarjeta lo pide) |
| **PG-26** Validación de lo que propone la IA | ✅ | Formato JSON fijo (si no, se rechaza); todo ejercicio existe, es posible en tus gyms y no está contraindicado; rangos de PG-25; máximo 2 reintentos y luego solo reglas; **cada rechazo queda registrado con su motivo** (`llamada_ia`); el usuario nunca ve un plan que no pasó la validación | — |
| **PG-27** Explicación del plan | ✅ | La IA explica en lenguaje simple; se guarda con la versión; máximo 3 líneas por día y 1 frase por ejercicio (se recorta si se pasa); si hay lesión y la explicación no la menciona, se agrega; palabras técnicas (hipertrofia, RIR, excéntrico…) se cambian por lenguaje simple | — |
| **PG-28** Elegir el gym y adaptar la sesión | ✅ | Con más de un gym, lo primero es elegir (el último usado primero y preseleccionado); con uno se salta. Toma el día que toca y lo adapta al inventario de ese gym (sin malogradas ni retiradas): si falta una máquina, otra del mismo músculo o un ejercicio sin equipo. Muestra qué cambió y por qué. Menos de 10 s. Se puede cambiar de gym y se vuelve a adaptar. Gym sin máquinas → solo sin equipo y sugiere tomar fotos. Si hoy no toca, ofrece adelantar el siguiente día | ⏭️ «Iniciar rutina» es del Sprint 4 (por eso se puede cambiar de gym en cualquier momento) |
| **PG-49** Control de costo y tiempo de la IA | 🟡 | Fotos ya reducidas antes de enviarse (Sprint 2). Registro de **cada** llamada con tokens, costo estimado y duración. Límites por usuario al día: 50 fotos, 3 búsquedas web, 5 planes con IA (+30 adaptaciones). Al llegar al límite de fotos: mensaje claro y «Elegir a mano». Costo diario: `python -m app.scripts.costo_ia` y `GET /api/ia/uso`. Alerta por correo al equipo si el costo del día supera el tope | ⏭️ La búsqueda en internet (PG-10) es del Sprint 5: su límite ya está configurado. La alerta necesita **SMTP real** y `IA_ALERTA_EMAIL` |

## ⚠️ La IA gratuita es lenta e irregular (lo medí)
Con `gemini-flash-lite-latest` en la capa gratuita, el **mismo** pedido tardó a veces 3 s y a veces 30 s, y genera
~30 tokens por segundo. Pedir la semana completa en una sola llamada tardaba **32–56 s**: imposible cumplir los 20 s.
Por eso:
1. La IA solo elige y explica (las series las pone el sistema): respuestas ~4 veces más cortas.
2. Se pide **un día por llamada, en paralelo**. Medido: cada día en 2,7–6,3 s cuando el servicio responde bien.
3. Si un pedido no volvió en 6 s se lanza **una copia** y se usa la que llegue primero (`IA_DUPLICAR_TRAS_SEG`, 0 = apagado).
4. Lo que no llega a tiempo usa la versión de reglas de ese día. El plan **siempre** sale en ≤ 18 s y siempre validado.

Resultado real hoy (servicio saturado, con errores 503 y 429): los planes salieron «IA + reglas» (2–3 de 4 días con IA).
Las copias gastan más pedidos por minuto: si ves muchos «límite gratuito por minuto», pon `IA_DUPLICAR_TRAS_SEG=0`.
**Con la capa de pago** los tiempos son estables y estas medidas casi no se notan.

## Respaldo con Replicate (Gemini 2.5 Flash, cobra por tokens)
Si Gemini gratis falla (saturado, límite por minuto, sin clave) o tarda, la misma llamada se hace en
`google/gemini-2.5-flash` de Replicate (`REPLICATE_API_TOKEN` en `backend/.env`). Acepta **texto e imágenes**, así
que respalda las fotos, el plan y la adaptación. Reglas:
- Gemini primero. Si hay respaldo, Gemini usa como mucho el 60 % del tiempo y el resto queda para Replicate.
- Las copias de los pedidos lentos van **directo a Replicate**.
- Replicate no tiene "esquema fijo": el esquema va en el texto y la respuesta pasa por la misma validación (PG-26).
- Su costo se registra con su propio precio (`REPLICATE_PRECIO_*`; verifícalo en la página del modelo).

Medido con tu token: foto real de prensa 45° **solo con Replicate** → `PRENSA_45` con 0,95 en 8,0 s; texto corto en
~2–3 s. ⚠️ **Con menos de USD 5 de saldo, Replicate permite solo 6 pedidos por minuto y de a uno**: el plan (5 pedidos
a la vez) recibió 429 en 4 de 5 y esos días cayeron a reglas. Para que el respaldo sirva en el plan hay que cargar
USD 5 o más en la cuenta de Replicate. Si Replicate pide esperar unos segundos y el tiempo alcanza, se espera y se
reintenta una vez.

## Decisiones que tomé y conviene que confirmes
1. **«Precaución» solo en reintroducción, también en los reemplazos** (PG-20). En el Sprint 2 los reemplazos mostraban
   «precaución» con la lesión activa; ahora no. Ajusté esa prueba del Sprint 2.
2. **Bajar grasa y salud general usan los rangos de «músculo»** (PG-25 solo define fuerza, músculo y resistencia).
3. **2–3 días seguidos (ej. lunes-martes-miércoles) no usan cuerpo completo**: chocaría con «nunca el mismo grupo en
   días seguidos», así que se usa torso/pierna o empuje/tirón/pierna. La explicación lo dice.
4. **El plan solo usa lo que hay en ALGUNO de tus gyms** (sin gyms registrados, todo el catálogo). La adaptación del
   día lo ajusta a un gym concreto.
5. **Con 1 día por semana** no alcanzan 4–8 ejercicios para los 6 grupos grandes: se avisa en vez de rechazar el plan.
6. **Límites:** el usuario regenera hasta 3 veces al día (PG-23); la IA arma hasta 5 planes al día (PG-49): la
   regeneración automática por lesión no cuenta para las 3, pero sí para las 5; pasado el límite se usan reglas.
   Los días se cuentan en hora UTC (en Bolivia el contador vuelve a cero a las 20:00).
7. **Privacidad:** a Gemini se le envía objetivo, nivel, edad, sexo, peso, % de grasa, masa muscular y la **zona**
   de cada lesión; nunca nombre, correo ni lo que el usuario escribió de su lesión (hay una prueba). Igual que con las
   fotos: en la capa gratuita Google puede usar esos datos → **capa de pago antes de tener usuarios reales**, y el
   texto del consentimiento (PG-05) debería mencionarlo.
8. Las 5 tablas nuevas (`rutina`, `rutina_dia`, `rutina_ejercicio`, `adaptacion_dia`, `llamada_ia`) se crean solas al
   arrancar; **no se modificó ninguna tabla existente**. Siguen faltando las migraciones (Alembic).

## API nueva
| Método | Ruta | Para qué |
|---|---|---|
| GET | `/api/plan` | Plan activo (se regenera solo si cambiaron las lesiones), días sugeridos, regeneraciones restantes |
| POST | `/api/plan` | Armar o regenerar `{"dias": ["lunes", …]}` · 429 `limite_regeneraciones` |
| GET | `/api/hoy?gym_id=&dia=&fecha=` | La sesión de hoy adaptada al gym (`fecha` = día local del celular) |
| GET | `/api/ia/uso` | Uso de IA del usuario hoy y sus límites |

## Pendiente de la Definición de terminado
- ✅ **Diagrama `.drawio`**: `rutina`, `rutina_dia` y `rutina_ejercicio` con sus campos nuevos + tablas `adaptacion_dia`
  y `llamada_ia` con sus relaciones (ábrelo en diagrams.net y acomoda si algo quedó apretado).
- ✅ **IA probada con casos reales**: 6 planes con Gemini real (de 3, 4 y 5 días, con la rodilla en recuperación);
  todos pasaron la validación semanal. Además se probó qué pasa cuando la IA falla, tarda o responde mal (pruebas
  automáticas). Ver la medición de arriba.
- **Revisión por otro integrante** y comentario en cada tarjeta de Trello.

## Probado
- **Backend:** 168 pruebas automáticas pasan (74 nuevas del Sprint 3, 11 del respaldo con Replicate). Además, un ensayo de las reglas con
  **2.286 combinaciones** (todos los días posibles × 3 objetivos × 2 niveles × 3 duraciones): todas válidas.
- **App** (navegador a 390 y 360 px, contra tu PostgreSQL y Gemini real): elegir gym → sesión de hoy adaptada con el
  cambio explicado y las marcas de precaución → plan semanal con escudo de lesión → regenerar (18 s, «IA + reglas»).
- **No probado:** teléfono físico; la alerta de costo con SMTP real.
