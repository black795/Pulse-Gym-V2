# Qué se reutilizó de tu proyecto anterior (black795/Pulse-gym)

Resumen: el **diseño visual y la forma de manejar la sesión** se aprovecharon. El **modelo de datos y la lógica de roles** se
reemplazaron, porque el nuevo enfoque tiene un solo tipo de usuario y otro negocio (entrenador IA, no administración de gimnasio).

## ✅ Reutilizado (adaptado)
| Del proyecto anterior | Ahora |
|---|---|
| Colores y tipografías (verde, neón, Sora/Manrope) en `index.css` | Igual, más reglas para celular (botones de 48 px, zonas seguras, 100dvh) |
| `Icons.tsx`, `Avatar.tsx` | Igual; se agregaron 5 iconos |
| `PantallaCarga`, `NoEncontrada` | Igual, adaptadas a celular |
| `lib/http.ts` (cliente de la API) | Reescrito: ahora entiende los códigos de error del backend (ej. "falta consentimiento") |
| `AuthContext`, guardias de ruta, `tokenStorage` | Simplificados: sin roles ni permisos; sesión de 30 días; si no hay internet NO se cierra la sesión |
| Patrón del backend: configuración, hash bcrypt, JWT, pruebas con TestClient | Mismo estilo, reescrito para el nuevo modelo |
| Pantallas de celular (Cámara, Confirmar, Entreno, Progreso, IA) | Guardadas en `referencia-prototipos/` para los Sprints 2–5 |

## 🔁 Reemplazado
- **Modelo de datos** (clientes, membresías, pagos, asistencia): no aplica al nuevo producto. Hay 15 tablas nuevas.
- **4 roles y permisos**: ahora hay un solo rol, "usuario".
- Login y registro: reescritos con bloqueo tras 5 intentos fallidos, recuperación de contraseña y consentimiento.

## ❌ Descartado
- Las 12 pantallas de administración (`pages/admin/*`), Sidebar y Topbar de escritorio, y las 22 pruebas de roles.
- El README anterior mencionaba un `docker-compose.yml` que no existía; ahora sí existe (opcional).

## 🔎 Hallazgos del repositorio anterior
- Los archivos binarios (png, zip…) estaban marcados para Git LFS en `.gitattributes`. Si subes los iconos de la PWA al repositorio, vas a necesitar LFS o quitar esa regla para `*.png`.
- Las pantallas móviles usaban datos de ejemplo escritos a mano; ninguna estaba conectada a un backend.
