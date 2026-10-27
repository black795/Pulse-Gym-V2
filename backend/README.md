# Backend — Pulse Gym v2

FastAPI + SQLAlchemy 2. Ver el README de la carpeta superior para arrancarlo.

- `app/api/routes/` — rutas (auth, perfil, lesiones, catálogo, gyms, fotos)
- `app/services/` — la lógica (ahí viven las reglas de negocio)
- `app/models/` — las 19 tablas (Sprint 2: gym, foto_maquina, reconocimiento_ia, gym_maquina)
- `app/services/ia_vision.py` — la IA que reconoce máquinas (Gemini o simulada)
- `app/services/fotos_storage.py` — guarda las fotos sin metadatos y arma los enlaces que vencen en 1 hora
- `app/scripts/cargar_catalogo.py` — carga/valida el catálogo (`--validar`, `--estricto`)
- `app/scripts/propuestas.py` — lista las máquinas que los usuarios propusieron (`--csv`)
- `app/scripts/probar_ia.py` — mide el acierto de la IA con una carpeta de fotos reales
- `tests/` — `pytest`
