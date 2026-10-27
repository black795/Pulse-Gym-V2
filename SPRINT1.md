# Sprint 1 — Base: cuenta, perfil y catálogo

Leyenda: ✅ hecho y probado · 🟡 hecho, pero falta algo que no puede resolver el código · ⬜ pendiente

| Tarjeta | Estado | Qué hay | Qué falta |
|---|---|---|---|
| **PG-01** Cuenta | ✅ | Registro, login, "olvidé mi contraseña" (enlace de 30 min, un solo uso), bloqueo de 15 min tras 5 intentos fallidos, sesión de 30 días, mensajes de login y recuperación que no revelan si un correo existe | Configurar SMTP real para enviar correos (hoy se imprimen en la terminal) |
| **PG-02** Perfil | ✅ | Registro en 3 pantallas (datos básicos → composición opcional → meta/nivel/días/minutos), IMC, historial de mediciones, edición desde Perfil | — |
| **PG-05** Consentimiento | 🟡 | Se pide antes de peso/altura/lesiones; aceptar, rechazar, retirar (borra los datos sensibles) y eliminar la cuenta; el backend bloquea (403) si no hay permiso; se guarda qué versión del texto aceptó cada persona | **El texto es un borrador**: debe revisarlo una persona con conocimiento legal antes de lanzar |
| **PG-15** Catálogo de máquinas | 🟡 | 42 máquinas con otros nombres comunes, cargadas desde JSON | **Fotos de referencia**: ninguna máquina tiene foto todavía (el validador lo avisa 42 veces). Son el insumo del reconocimiento del Sprint 2 |
| **PG-16** Catálogo de ejercicios | 🟡 | 100 ejercicios (34 sin equipo), con músculos, dificultad, instrucciones y contraindicaciones | **Revisión del entrenador**: todas las contraindicaciones están marcadas como "no revisadas" y no deben usarse con usuarios reales hasta que alguien las valide |
| **PG-17** Alternativas | ✅ | Reemplazos en orden máquina → peso libre → sin equipo, respetando lesiones activas y en reintroducción | Se conecta a la pantalla en el Sprint 3 (hoy es solo API: `/api/catalogo/ejercicios/{id}/alternativas`) |
| **PG-18** Script de carga | ✅ | `python -m app.scripts.cargar_catalogo`: valida antes de insertar, no duplica, actualiza lo que cambió | — |
| **PG-19** Lesiones | ✅ | Zonas fijas, tipo aguda/crónica, estados activa → reintroducción → recuperada, historial, aviso "no reemplaza a un médico" | — |
| **PG-50** Entrega incremental | ✅ | Todo corre con 2 comandos y trae cuenta demo; PWA instalable con modo sin conexión básico | La demo "en entorno de prueba" requiere publicar (hosting con HTTPS) |

## Decisiones que tomé y conviene que confirmes
1. **Vite en lugar de Next.js**: tu repo anterior ya usaba Vite + React; para una PWA que habla con un backend aparte es más simple. Cambiarlo después es posible pero costoso.
2. **Consentimiento**: lo interpreté como "no puedes guardar peso, altura, % de grasa, masa muscular ni lesiones sin aceptar; sí puedes crear cuenta y usar la app". Si quieres que sea obligatorio para todo, es un cambio pequeño.
3. **PWA sin librerías**: manifest, service worker e iconos hechos a mano (sin plugin), para que entiendas qué hace cada pieza.
4. Las tablas se crean al arrancar (`create_all`); aún no hay migraciones (Alembic). Conviene agregarlas antes de tener usuarios reales.

## Probado
- Backend: 59 pruebas automáticas pasan; el esquema compila para PostgreSQL.
- App: recorrido completo en un navegador de celular simulado (registro → consentimiento → 3 pasos → lesión → medición → retirar consentimiento → recargar → cerrar sesión → error de login → modo sin conexión). **No probado en un teléfono físico ni con SMTP real.**
