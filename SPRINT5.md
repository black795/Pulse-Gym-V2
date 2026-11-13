# Sprint 5 — Progreso, historial de máquinas y pesos sugeridos

Leyenda: ✅ hecho y probado · 🟡 hecho, pero falta algo que no puede resolver el código · ⏭️ depende de otro sprint

> Las tarjetas se tomaron del **Módulo F** de `docs/guia-diseno-figma-pulse-gym-v2.md` (PG-38 a PG-43, PG-46) más el
> pedido de «historial de máquinas con mis pesos» y «que la IA dé pesos iniciales y luego progrese con el historial».
> PG-44 (recordatorios) y PG-45 (mediciones) no entraron en este sprint.

## Cómo probarlo en 3 minutos
1. Arranca todo como siempre y entra con `demo@pulsegym.app` / `Pulse2026!`.
2. **Plan** → regenera el plan: cada ejercicio muestra «✨ Peso sugerido: X kg · primera vez, estimado por la IA».
3. **Hoy** → **▶ Iniciar rutina de hoy**: cada ejercicio trae la pastilla con el peso y el kg ya escrito en la tabla.
   Marca todas las series al tope del rango de repeticiones y finaliza.
4. Vuelve a iniciar (o espera a tu próximo día): ahora dice «📈 Completaste 3×10 con 40 kg la última vez → hoy intenta 42,5 kg».
5. Pestaña **Progreso**: racha, alertas, **Mis máquinas y pesos** (solo las que ya usaste) y el historial de sesiones.
   Toca una máquina para ver su gráfico de evolución con los récords 🏆.
6. Finaliza una sesión con pocas series → en el resumen, **«Olvidé marcar series»**. En **Hoy** o **Progreso**,
   **Registrar entrenamiento pasado**.

## Estado por tarjeta

| Tarjeta | Estado | Qué hay | Qué falta |
|---|---|---|---|
| **Historial de máquinas** (pedido) | ✅ | Lista solo de los ejercicios/máquinas que ya hiciste: última vez, récord, cambio desde la primera vez y peso para la próxima. Filtro Máquinas / Peso libre / Sin equipo. Detalle con gráfico del peso más alto por sesión y cada sesión con sus series. Cada usuario ve solo lo suyo (404 si nunca lo hizo) | — |
| **Pesos iniciales con IA** (pedido) | 🟡 | Al armar el plan, la IA propone `peso_kg` por ejercicio usando el perfil (nivel, sexo, edad, peso) y los pesos que ya levantas. **Se acota** entre 0,5× y 1,5× de una estimación por reglas y se guarda en `rutina.parametros.pesos_base`. Si la IA no responde o no manda peso, se usa la de reglas | La estimación por reglas (fracción del peso corporal) es una **propuesta**: debe revisarla un entrenador |
| **PG-41** Sobrecarga progresiva | 🟡 | Doble progresión con tu historial: todas las series al tope del rango → sube 2,5 kg (varias articulaciones) o 1 kg (una), nunca más del 10 %; si no → mismo peso y 1 repetición más; si no llegaste al mínimo → baja. Con lesión en recuperación no sube. Se ve en Plan, Hoy y la sesión en vivo, y llena el kg de la tabla | Regla **propuesta**, a validar por un entrenador |
| **PG-42** Retorno tras ausencia | ✅ | Si un ejercicio no se hace hace 14 días o más, su peso baja 10 %. Alerta «Volviste después de N semanas» en Progreso y aviso en Hoy | — |
| **PG-43** Estancamiento | 🟡 | Alerta si llevas 3 sesiones o más (en 2 semanas o más) con el mismo peso máximo sin más repeticiones; con consejo y enlace al gráfico | La guía propone un botón «¿ajustamos el rango de repeticiones?»: no cambia el plan solo (decisión 5) |
| **PG-38** Racha y constancia | ✅ | (ya estaba en el trabajo previo) Ahora se muestra en **Hoy** (3 indicadores) y en **Progreso** | — |
| **PG-39** Olvidé marcar / entrenamiento pasado | ✅ | En una sesión **parcial** (hasta 48 h): completa las series que faltan con tu último peso de hoy (o el sugerido) y el mínimo de repeticiones → queda **Manual**. «Registrar entrenamiento pasado» (hasta 7 días): eliges fecha, día del plan y gym; el formulario trae el peso sugerido. No se puede registrar dos veces el mismo día del plan en la misma fecha | — |
| **PG-40** Panel de récords | ✅ | Récord por máquina en la lista y 🏆 en el gráfico y en cada sesión | — |
| **PG-46** Historial de sesiones | ✅ | (ya estaba en el backend) Pantalla con insignia Completa / Parcial / Manual y «Ver más» | — |

## Decisiones que tomé y conviene que confirmes
1. **La IA propone, las reglas acotan**: el peso de la IA solo se usa la primera vez y siempre dentro de 0,5×–1,5× de la
   estimación por reglas. Con historial manda la progresión por reglas (no la IA): es predecible y no gasta IA.
2. **«Manual» cuenta para la racha** si llega al 80 % de las series (igual que una completa), sin exigir tiempo.
3. **Las series agregadas con «Olvidé marcar series» nunca son récord** (no se midieron), y usan el mínimo de repeticiones.
4. **Un entrenamiento pasado** se ubica al mediodía de esa fecha. Sus récords se comparan con lo anterior, pero no se
   recalculan los récords de sesiones posteriores.
5. **PG-43 solo avisa**: cambiar el rango de repeticiones del plan sería cambiar una regla de negocio (PG-25).
6. **La pestaña Progreso** se agregó a la barra inferior (6 pestañas).
7. **Base de datos: ninguna tabla nueva ni modificada.** Los pesos de la IA van en el JSON `parametros` del plan, que ya
   existía; el estado `manual` ya estaba en `db/init_schema_v2.sql`.

## API nueva
| Método | Ruta | Para qué |
|---|---|---|
| GET | `/api/progreso/ejercicios?fecha=` | Historial de máquinas y pesos (solo lo que ya hiciste) |
| GET | `/api/progreso/ejercicios/{id}?fecha=` | Evolución de un ejercicio · 404 si nunca lo hiciste |
| GET | `/api/progreso/alertas?fecha=` | PG-42 retorno y PG-43 estancamiento |
| POST | `/api/sesiones/{id}/completar` | PG-39 «olvidé marcar series» · 409 `no_parcial` / `fuera_de_plazo` |
| POST | `/api/sesiones/pasadas` | PG-39 registrar entrenamiento pasado · 409 `ya_registrada` · 400 `fecha_invalida`, `ejercicio_invalido`, `sin_series` |

Campos nuevos (opcionales, no rompen la app anterior): `peso_sugerido` en los ejercicios de `/api/plan` y `/api/hoy`;
`sugerencia` en los ejercicios de la sesión en curso; estado `manual` en sesiones y resúmenes.

## Probado
- **Backend:** 246 pruebas automáticas pasan (42 nuevas: 28 de reglas puras en `test_progresion.py` y 14 de API en
  `test_pesos.py`; además se corrigió `test_progreso.py`, que fallaba según la hora del día).
- **Frontend:** `npm run build` (revisión de tipos y compilación) sin errores.
- **No probado:** la app en el navegador ni en un teléfono (no se levantaron servidores), ni la IA real de Gemini con
  el campo `peso_kg` (las pruebas usan la IA simulada).
