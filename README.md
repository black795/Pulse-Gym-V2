# Pulse Gym v2 — Entrenador IA (Sprints 1 a 3)

App web para celular (PWA) que arma tu entrenamiento según tu cuerpo, tus lesiones y las máquinas de tu gimnasio.
Incluye el **Sprint 1** (cuenta, perfil, consentimiento, lesiones y catálogo), el **Sprint 2** (mis gyms, fotos de
máquinas reconocidas con IA, inventario e implementos) y el **Sprint 3** (plan semanal con reglas + IA, validación,
explicación, elegir el gym y adaptar la sesión del día, límites y costo de la IA).
Estado de cada tarjeta: `SPRINT1.md`, `SPRINT2.md` y `SPRINT3.md`.

```
pulse-gym-v2/
├── backend/               API (Python + FastAPI). 168 pruebas automáticas.
│   └── catalogo/          Los 4 archivos JSON con máquinas y ejercicios (los edita el equipo)
├── frontend/              La app de celular (React + Vite), instalable como PWA
├── referencia-prototipos/ Pantallas viejas de la v1 para usar en sprints futuros
├── REUTILIZACION.md       Qué se aprovechó del proyecto anterior y qué se descartó
├── SPRINT1.md             Estado honesto de cada tarjeta del Sprint 1
├── SPRINT2.md             Ídem Sprint 2 (+ cómo activar la IA gratuita)
├── SPRINT3.md             Ídem Sprint 3 (+ qué tan rápida es la IA gratuita)
└── docker-compose.yml     (opcional) PostgreSQL
```

## Cómo correrlo en tu computador (2 terminales)

Necesitas Python 3.11+ y Node 20+.

**Terminal 1 — backend**
```
cd backend
python -m venv .venv
.venv\Scripts\activate          (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          (Mac/Linux: cp .env.example .env)
uvicorn app.main:app --reload
```
Al arrancar crea la base de datos sola, carga el catálogo (42 máquinas, 100 ejercicios) y una cuenta de prueba:
`demo@pulsegym.app` / `Pulse2026!`. Documentación de la API: http://localhost:8000/docs

**Terminal 2 — app de celular**
```
cd frontend
npm install
npm run dev
```
Abre http://localhost:5173. En el computador se ve como un celular centrado; para verla de verdad en tu teléfono,
abre la dirección de red que muestra Vite (misma wifi) o usa las herramientas de desarrollador → modo móvil.

Los correos de "olvidé mi contraseña" **se imprimen en la terminal del backend** (`CORREO_MODO=consola`):
copia el enlace de ahí. Para enviarlos de verdad, configura SMTP en `.env`.

## Pruebas
```
cd backend && pytest          # 168 pruebas
cd frontend && npm run build  # revisa tipos y compila
```

## IA para reconocer máquinas (Sprint 2)
Sin configurar nada usa una **IA simulada** (para probar las pantallas). Para la real y gratuita, crea una clave en
https://aistudio.google.com/apikey y ponla en `backend/.env` como `GEMINI_API_KEY=...`. Opcional: `REPLICATE_API_TOKEN=...`
como respaldo pagado por tokens si Gemini falla o tarda (ver `SPRINT3.md`). Detalles y advertencia de
privacidad en `SPRINT2.md`. Las fotos se guardan en `backend/uploads/` (privada, no se sube a GitHub).

**Cámara desde el celular:** la cámara *dentro* de la app necesita HTTPS. Abriendo la app por la wifi
(`http://192.168…:5173`) se usa la cámara normal del celular, que funciona igual.

## Plan semanal (Sprint 3)
Pestaña **Plan**: eliges los días y la IA arma la semana dentro de reglas fijas (lesiones, equipo, series y descansos);
todo se valida antes de mostrarse y, si la IA falla o tarda, se usan solo las reglas (nunca más de 18 s).
Pestaña **Hoy**: eliges el gym y ves la sesión del día adaptada a sus máquinas. Costo de la IA para el equipo:
`python -m app.scripts.costo_ia`. Detalles y medición de la IA gratuita en `SPRINT3.md`.

## Instalarla como app (PWA)
Solo funciona con la versión publicada (`npm run build`, servida por HTTPS): en el celular, menú del navegador →
"Instalar app" / "Añadir a pantalla de inicio". En desarrollo (`npm run dev`) el modo offline está apagado a propósito.

## Catálogo de máquinas y ejercicios
Se edita en `backend/catalogo/*.json` y se carga con `python -m app.scripts.cargar_catalogo`
(`--validar` solo revisa, `--estricto` además exige fotos). Repetirlo no duplica nada.
