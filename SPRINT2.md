# Sprint 2 — Mi gym con IA (fotos)

Leyenda: ✅ hecho y probado · 🟡 hecho, pero falta algo que no puede resolver el código · ⏭️ depende de otro sprint

## Cómo probarlo en 2 minutos
1. Arranca todo como siempre (`INICIAR_PULSE_GYM.bat`, o backend + frontend a mano).
2. Entra con `demo@pulsegym.app` / `Pulse2026!` → pestaña **Mis gyms** → crea un gym.
3. **Agregar máquinas con foto** → «Tomar fotos» (cámara dentro de la app) o «Galería» (varias a la vez).
4. Cada foto se sube, la IA la reconoce y se abre la hoja para confirmar o elegir.

Sin clave de IA funciona con la **IA simulada** (sugiere 3 máquinas reales del catálogo al azar): sirve para probar
todas las pantallas. Para reconocimiento de verdad, ver «IA gratuita» abajo.

## IA gratuita (Google Gemini)
1. Entra a https://aistudio.google.com/apikey con una cuenta de Google → «Create API key» (gratis, sin tarjeta).
2. En `backend/.env`: `GEMINI_API_KEY=tu_clave` (deja `IA_PROVEEDOR=auto`).
3. El backend se recarga solo. En la hoja de revisión verás «IA: gemini-flash-latest · 2.3 s».

⚠️ **Privacidad:** en la capa gratuita, Google puede usar lo que se le envía para mejorar sus productos. Sirve para
probar con tus propias fotos; **antes de tener usuarios reales** hay que pasar a la capa de pago (o a la API de Claude
que figura en el stack) — PG-48 dice que las fotos solo se usan para reconocer la máquina.

Para cambiar de proveedor después, solo se toca `backend/app/services/ia_vision.py` (se agrega una función a
`PROVEEDORES`). El resto de la app no cambia.

### Medir la calidad (meta de PG-08: 80% en 30 fotos reales)
```
cd backend
python -m app.scripts.probar_ia carpeta_fotos --csv resultados.csv
```
`carpeta_fotos/` lleva una subcarpeta por código de máquina (`PRENSA_45/`, `HACK_SQUAT/`…) y opcionalmente
`NO_ES_MAQUINA/`. El script informa aciertos en el 1.er puesto, en el top 3, errores y tiempos.

## Estado por tarjeta

| Tarjeta | Estado | Qué hay | Qué falta |
|---|---|---|---|
| **PG-06** Registrar mis gyms | ✅ | Varios gyms (máx. 5), nombre obligatorio y ubicación opcional, sin nombres repetidos (sin importar mayúsculas ni espacios), renombrar, eliminar con confirmación, se recuerda el último usado (se ve primero y en Inicio), un gym nuevo arranca vacío y guía a tomar fotos | «Eliminar no borra el historial de sesiones»: las sesiones aún no existen (Sprint 4); cuando se creen, `sesion_entreno.gym_id` debe ser `ON DELETE SET NULL` como dice el diagrama |
| **PG-07** Tomar foto | 🟡 | Cámara dentro de la app con guía de encuadre y modo recorrido (varias seguidas), galería con selección múltiple, JPG/PNG/HEIC hasta 10 MB, se reduce a 1280 px **en el celular** antes de subir, barra de progreso con «Cancelar», si se niega el permiso explica cómo activarlo y ofrece la galería, sin señal la foto queda guardada en el celular y se sube sola al volver la conexión (también si se cierra la app) | **Probar en un teléfono físico.** La cámara dentro de la app exige HTTPS: desde el celular por wifi (`http://192.168…`) se usa la cámara del sistema (funciona igual, pero sin la guía dibujada). Con la app publicada en HTTPS se ve la cámara integrada |
| **PG-08** Reconocimiento con IA | ✅ | Envía la foto + las 42 máquinas del catálogo al modelo; responde hasta 3 máquinas con confianza; códigos inventados se descartan (doble control: el modelo solo puede elegir de la lista y el backend lo vuelve a validar); «no es una máquina» pide otra foto; si falla o tarda más de 15 s, error con «Reintentar» y «Elegir a mano»; cada intento queda guardado (modelo, máquina, confianza, puesto). **Probado con Google Gemini Vision real (`gemini-flash-lite-latest`): 5/5 aciertos top-1 (100%) en 2,6–3,6 s + rechazo de foto que no es máquina** | Ampliar el lote a 30 fotos tomadas con el celular en gimnasios locales con `python -m app.scripts.probar_ia` |
| **PG-09** Confirmar o elegir | ✅ | Confianza ≥ 0,85 → solo confirma; menor → 2–3 opciones con foto de referencia, nombre, músculo principal y % de confianza; «Ninguna es»; búsqueda a mano por nombre, otros nombres (ej. «leg press») o músculo, sin importar tildes; nada entra al inventario sin confirmar; se guarda qué eligió el usuario y en qué puesto estaba | El umbral 0,85 se calibra con los datos reales (ver consulta abajo). «Ninguna es» deja la foto lista para la búsqueda en internet (PG-10, Sprint 5); mientras tanto se busca a mano |
| **PG-12** Sin duplicados | ✅ | Si la máquina ya está, avisa y ofrece **actualizar su foto** (la vieja se borra); restricción única `(gym_id, maquina_id)` en la base; varias unidades = una sola fila; quitar una máquina agregada por error | — |
| **PG-13** Malograda o retirada | 🟡 | Estados disponible / malograda / ya no está, con un toque desde el inventario; «malograda» vuelve con un toque y «retirada» pide confirmación; se guarda la fecha de cada cambio; las no disponibles se excluyen de `/api/gyms/{id}/disponibles` y de las alternativas (`?gym_id=`) | ⏭️ Cambiar el estado «desde la sesión» y «re-adaptar la sesión si una máquina del día se malogra» dependen de la sesión del día (Sprints 3 y 4); la regla ya está lista para usarse |
| **PG-14** Implementos | ✅ | Lista rápida de 10 implementos (la del tablero), peso máximo de mancuernas opcional, editables en cualquier momento; los ejercicios con peso corporal siempre están disponibles. Cada implemento «habilita» máquinas del catálogo (ej. mancuernas → `MANCUERNAS`) para el plan del Sprint 3 | — |
| **PG-47** Pensado para celular | 🟡 | Probado a 360 px sin desborde y botones de 44 px o más; cámara; PWA instalable (del Sprint 1) | **Probar en Chrome (Android) y Safari (iPhone) reales** y medir la carga en 4G (requiere la app publicada). El sonido es del Sprint 4. Vibración y pantalla bloqueada quedan fuera, como dice la tarjeta |
| **PG-48** Privacidad de las fotos | 🟡 | Las fotos se guardan fuera de cualquier carpeta pública y **sin metadatos** (se borra la ubicación GPS del celular); solo se ven con un enlace firmado que vence en 1 hora y solo el dueño lo recibe; otro usuario recibe «no existe»; el service worker no las guarda en caché; al borrar el gym o la cuenta se borran los archivos; aviso de encuadrar sin personas | **HTTPS** depende del hosting (Vercel/Render lo dan). **Gemini gratuito** puede usar las fotos (ver arriba). «El equipo puede ver las de máquinas propuestas» llega con PG-10 |

## Decisiones que tomé y conviene que confirmes
1. **Gemini en vez de Claude por ahora**, porque pediste una API gratuita. El cambio a otro modelo es de un archivo.
2. **Fotos en el disco del servidor** (`backend/uploads/`), no en Cloudinary todavía: así se prueba sin otra cuenta.
   El código de almacenamiento está aislado en `services/fotos_storage.py` para cambiarlo antes de publicar
   (en Render/Railway el disco se borra en cada despliegue).
3. **Cuando borras una máquina o una foto**, se borra el archivo pero se guarda lo que respondió la IA y lo que eligió
   el usuario (sin la imagen): son los datos para calibrar los umbrales.
4. **Si vuelves a fotografiar una máquina «retirada»** y eliges actualizar la foto, vuelve a «disponible».
5. Las tablas se crearon con `create_all` (igual que en el Sprint 1). Sigue pendiente agregar migraciones
   (Alembic) antes de tener usuarios reales.

## Pendiente de la Definición de terminado
- ✅ **Diagrama `.drawio`**: actualizado `docs/Pulse_Gym_Base_de_Datos_v2.drawio` con todos los campos del Sprint 2 en `gym`, `foto_maquina`, `reconocimiento_ia` y `gym_maquina`.
- **Revisión por otro integrante** y comentario en cada tarjeta de Trello.

### Consulta para calibrar el umbral (PG-09)
```sql
-- ¿En qué puesto estaba la máquina que eligió el usuario, según la confianza de la 1.ª sugerencia?
SELECT f.id, f.eleccion, f.elegida_puesto, r.confianza AS confianza_primera
FROM foto_maquina f JOIN reconocimiento_ia r ON r.foto_id = f.id AND r.puesto = 1
WHERE f.eleccion IS NOT NULL AND r.intento = f.ia_intentos;
```

## Probado
- **Backend:** 94 pruebas automáticas pasan (35 nuevas del Sprint 2: gyms, fotos, IA, duplicados, estados,
  implementos, enlaces temporales, borrado de archivos).
- **App** (navegador simulando un celular de 390 y 360 px, contra tu PostgreSQL): crear gym → implementos y peso de
  mancuernas → subir 3 fotos de la galería → elegir entre opciones → buscar a mano («leg press») → duplicado con
  «actualizar foto» → malograda / retirada con confirmación → foto sin conexión que sobrevive a recargar y se sube
  al volver la señal → «Ninguna es» → cámara en modo recorrido (2 fotos seguidas) → eliminar gym (se borran los 6
  archivos) → enlace de foto falsificado rechazado.
- **No probado:** teléfono físico, IA real (Gemini) con fotos reales, HEIC desde un iPhone de verdad.
