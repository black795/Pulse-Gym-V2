"""PG-18: carga y validación del catálogo desde los archivos JSON de la carpeta `backend/catalogo/`.

Uso (desde la carpeta backend):
    python -m app.scripts.cargar_catalogo --validar     # solo revisa los archivos, no toca la base
    python -m app.scripts.cargar_catalogo               # valida y carga (se puede correr muchas veces)
    python -m app.scripts.cargar_catalogo --estricto    # además exige foto de referencia en cada máquina

Volver a correrlo NO duplica datos: cada fila se identifica por su código y solo se actualiza lo que cambió.
"""
import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Ejercicio, EjercicioContraindicacion, EjercicioMaquina, EjercicioMusculo, GrupoMuscular,
    MaquinaCatalogo, MaquinaFotoRef, ZonaLesion,
)

CARPETA = Path(__file__).resolve().parents[2] / "catalogo"

TIPOS_MAQUINA = {"maquina_guiada", "polea", "peso_libre", "estructura", "cardio"}
TIPOS_QUE_SON_MAQUINA = {"maquina_guiada", "polea", "cardio"}
TIPOS_QUE_SON_PESO_LIBRE = {"peso_libre", "estructura"}
DIFICULTADES = {"facil", "media", "dificil"}
CATEGORIAS = {"maquina", "peso_libre", "sin_equipo"}
NIVELES = {"evitar", "precaucion"}
PATRON_CODIGO = re.compile(r"^[A-Z0-9_]+$")

# Metas de la carga inicial (tarjetas PG-15 y PG-16). No bloquean, pero el informe avisa si no se cumplen.
META_MAQUINAS = (30, 50)
META_EJERCICIOS = 80
META_SIN_EQUIPO = 20
MIN_ALTERNATIVAS_POR_GRUPO = 3  # PG-17


@dataclass
class Informe:
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    resumen: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errores


def leer_datos(carpeta: Path = CARPETA) -> dict:
    def leer(nombre: str):
        with open(carpeta / nombre, encoding="utf-8") as f:
            return json.load(f)

    return {
        "grupos": leer("grupos_musculares.json"),
        "zonas": leer("zonas_lesion.json"),
        "maquinas": leer("maquinas.json"),
        "ejercicios": leer("ejercicios.json"),
    }


def validar(datos: dict, estricto: bool = False) -> Informe:
    """Revisa los datos ANTES de insertar nada: códigos únicos, referencias que existen, metas del catálogo."""
    inf = Informe()
    err, avi = inf.errores, inf.avisos

    def codigos_unicos(items: list[dict], que: str) -> set[str]:
        vistos: set[str] = set()
        for it in items:
            c = it.get("codigo")
            if not c:
                err.append(f"{que}: hay un elemento sin código ({it.get('nombre', '?')}).")
            elif c in vistos:
                err.append(f"{que}: el código «{c}» está repetido.")
            vistos.add(c)
        return vistos

    grupos = codigos_unicos(datos["grupos"], "Grupos musculares")
    zonas = codigos_unicos(datos["zonas"], "Zonas de lesión")
    maquinas = codigos_unicos(datos["maquinas"], "Máquinas")
    codigos_ejercicio = codigos_unicos(datos["ejercicios"], "Ejercicios")

    tipo_de = {m["codigo"]: m.get("tipo") for m in datos["maquinas"] if m.get("codigo")}
    for m in datos["maquinas"]:
        c = m.get("codigo", "")
        if not PATRON_CODIGO.match(c):
            err.append(f"Máquina «{c}»: el código debe ir en MAYÚSCULAS, números y guion bajo (ej. PRENSA_45).")
        if m.get("tipo") not in TIPOS_MAQUINA:
            err.append(f"Máquina «{c}»: tipo «{m.get('tipo')}» no válido ({', '.join(sorted(TIPOS_MAQUINA))}).")
        if not m.get("nombre"):
            err.append(f"Máquina «{c}»: falta el nombre.")
        if not m.get("fotos"):
            (err if estricto else avi).append(f"Máquina «{c}»: no tiene foto de referencia (PG-15 pide al menos 1).")

    usadas: set[str] = set()
    por_grupo: dict[str, list[dict]] = {g: [] for g in grupos}
    for e in datos["ejercicios"]:
        c = e.get("codigo", "?")
        if e.get("dificultad") not in DIFICULTADES:
            err.append(f"Ejercicio «{c}»: dificultad «{e.get('dificultad')}» no válida.")
        cat = e.get("categoria_equipo")
        if cat not in CATEGORIAS:
            err.append(f"Ejercicio «{c}»: categoria_equipo «{cat}» no válida.")
        if not e.get("instrucciones"):
            err.append(f"Ejercicio «{c}»: faltan las instrucciones.")

        principal = e.get("musculo_principal")
        if principal not in grupos:
            err.append(f"Ejercicio «{c}»: necesita un músculo principal que exista (recibió «{principal}»).")
        else:
            por_grupo[principal].append(e)
        for s in e.get("musculos_secundarios", []):
            if s not in grupos:
                err.append(f"Ejercicio «{c}»: el músculo secundario «{s}» no existe.")
            if s == principal:
                err.append(f"Ejercicio «{c}»: «{s}» no puede ser principal y secundario a la vez.")

        for mc in e.get("maquinas", []):
            if mc not in maquinas:
                err.append(f"Ejercicio «{c}»: la máquina «{mc}» no existe.")
            usadas.add(mc)
        tipos = {tipo_de.get(mc) for mc in e.get("maquinas", [])}
        if cat == "sin_equipo" and e.get("maquinas"):
            err.append(f"Ejercicio «{c}»: es «sin_equipo» pero tiene máquinas asignadas.")
        if cat == "maquina" and not (tipos & TIPOS_QUE_SON_MAQUINA):
            err.append(f"Ejercicio «{c}»: es de «maquina» pero ninguna de sus máquinas es máquina/polea/cardio.")
        if cat == "peso_libre" and not (tipos & TIPOS_QUE_SON_PESO_LIBRE):
            err.append(f"Ejercicio «{c}»: es de «peso_libre» pero no tiene pesas ni estructura asignada.")

        zonas_vistas: set[str] = set()
        for ci in e.get("contraindicaciones", []):
            if ci.get("zona") not in zonas:
                err.append(f"Ejercicio «{c}»: la zona de lesión «{ci.get('zona')}» no existe.")
            if ci.get("nivel") not in NIVELES:
                err.append(f"Ejercicio «{c}»: nivel «{ci.get('nivel')}» no válido (evitar | precaucion).")
            if ci.get("zona") in zonas_vistas:
                err.append(f"Ejercicio «{c}»: la zona «{ci.get('zona')}» está repetida en contraindicaciones.")
            zonas_vistas.add(ci.get("zona"))

    for mc in sorted(maquinas - usadas):
        err.append(f"Máquina «{mc}»: no tiene ningún ejercicio asociado (PG-15 pide al menos 1).")

    for g, lista in por_grupo.items():
        if len(lista) < MIN_ALTERNATIVAS_POR_GRUPO:
            err.append(f"Grupo «{g}»: tiene {len(lista)} ejercicios; PG-17 pide al menos {MIN_ALTERNATIVAS_POR_GRUPO}.")
        if not any(x.get("categoria_equipo") == "sin_equipo" for x in lista):
            err.append(f"Grupo «{g}»: no tiene ningún ejercicio sin equipo como alternativa (PG-17).")

    n_sin = sum(1 for e in datos["ejercicios"] if e.get("categoria_equipo") == "sin_equipo")
    if len(datos["ejercicios"]) < META_EJERCICIOS:
        avi.append(f"Meta PG-16: {len(datos['ejercicios'])} ejercicios cargados; se piden al menos {META_EJERCICIOS}.")
    if n_sin < META_SIN_EQUIPO:
        avi.append(f"Meta PG-16: {n_sin} ejercicios sin equipo; se piden al menos {META_SIN_EQUIPO}.")
    if not META_MAQUINAS[0] <= len(datos["maquinas"]) <= META_MAQUINAS[1]:
        avi.append(f"Meta PG-15: {len(datos['maquinas'])} máquinas; la meta es {META_MAQUINAS[0]}–{META_MAQUINAS[1]}.")

    inf.resumen = {
        "grupos": len(datos["grupos"]), "zonas": len(datos["zonas"]), "maquinas": len(datos["maquinas"]),
        "ejercicios": len(datos["ejercicios"]), "sin_equipo": n_sin,
    }
    return inf


# ---------------------------------------------------------------- carga a la base de datos
def _set(obj, campo: str, valor) -> bool:
    if getattr(obj, campo) != valor:
        setattr(obj, campo, valor)
        return True
    return False


def cargar(db: Session, datos: dict | None = None, estricto: bool = False) -> tuple[Informe, dict[str, int]]:
    """Valida y, si todo está bien, inserta o actualiza. Devuelve (informe, conteo de creados/actualizados)."""
    datos = datos or leer_datos()
    informe = validar(datos, estricto)
    conteo = {"creados": 0, "actualizados": 0}
    if not informe.ok:
        return informe, conteo

    def upsert_simple(modelo, items: list[dict]) -> dict[str, object]:
        existentes = {o.codigo: o for o in db.scalars(select(modelo))}
        for it in items:
            o = existentes.get(it["codigo"])
            if o is None:
                o = modelo(codigo=it["codigo"], nombre=it["nombre"])
                db.add(o)
                existentes[it["codigo"]] = o
                conteo["creados"] += 1
            elif _set(o, "nombre", it["nombre"]):
                conteo["actualizados"] += 1
        db.flush()
        return existentes

    grupos = upsert_simple(GrupoMuscular, datos["grupos"])
    zonas = upsert_simple(ZonaLesion, datos["zonas"])

    # --- máquinas
    maquinas = {m.codigo: m for m in db.scalars(select(MaquinaCatalogo))}
    for it in datos["maquinas"]:
        m = maquinas.get(it["codigo"])
        cambio = False
        if m is None:
            m = MaquinaCatalogo(codigo=it["codigo"], nombre=it["nombre"], tipo=it["tipo"], otros_nombres=[])
            db.add(m)
            maquinas[it["codigo"]] = m
            conteo["creados"] += 1
        else:
            cambio |= _set(m, "nombre", it["nombre"]) | _set(m, "tipo", it["tipo"])
        cambio |= _set(m, "otros_nombres", list(it.get("otros_nombres", [])))
        cambio |= _set(m, "activa", bool(it.get("activa", True)))
        urls = list(it.get("fotos", []))
        if urls and [f.url for f in m.fotos] != urls:  # sin fotos en el JSON, se respetan las que ya hubiera en la base
            m.fotos = [MaquinaFotoRef(url=u, orden=i) for i, u in enumerate(urls)]
            cambio = True
        if cambio and m.id is not None:
            conteo["actualizados"] += 1
    db.flush()

    # --- ejercicios
    ejercicios = {e.codigo: e for e in db.scalars(select(Ejercicio))}
    for it in datos["ejercicios"]:
        e = ejercicios.get(it["codigo"])
        nuevo = e is None
        if nuevo:
            e = Ejercicio(
                codigo=it["codigo"], nombre=it["nombre"], dificultad=it["dificultad"],
                categoria_equipo=it["categoria_equipo"], instrucciones=it["instrucciones"],
            )
            db.add(e)
            ejercicios[it["codigo"]] = e
            conteo["creados"] += 1
        cambio = False
        cambio |= _set(e, "nombre", it["nombre"]) | _set(e, "dificultad", it["dificultad"])
        cambio |= _set(e, "categoria_equipo", it["categoria_equipo"]) | _set(e, "instrucciones", it["instrucciones"])
        cambio |= _set(e, "multiarticular", bool(it.get("multiarticular", False)))
        cambio |= _set(e, "activo", bool(it.get("activo", True)))

        musculos = {(it["musculo_principal"], "principal")} | {(s, "secundario") for s in it.get("musculos_secundarios", [])}
        actual = {(x.grupo.codigo, x.rol) for x in e.musculos} if not nuevo else set()
        if musculos != actual:
            e.musculos = [EjercicioMusculo(grupo_id=grupos[g].id, rol=r) for g, r in sorted(musculos)]
            cambio = True

        maqs = set(it.get("maquinas", []))
        actual_m = {x.maquina.codigo for x in e.maquinas} if not nuevo else set()
        if maqs != actual_m:
            e.maquinas = [EjercicioMaquina(maquina_id=maquinas[c].id) for c in sorted(maqs)]
            cambio = True

        contra = {(c["zona"], c["nivel"]) for c in it.get("contraindicaciones", [])}
        actual_c = {(x.zona.codigo, x.nivel) for x in e.contraindicaciones} if not nuevo else set()
        if contra != actual_c:
            e.contraindicaciones = [EjercicioContraindicacion(zona_id=zonas[z].id, nivel=n) for z, n in sorted(contra)]
            # Si cambian las contraindicaciones, un entrenador debe volver a revisarlas.
            e.contraindicaciones_revisadas = False
            cambio = True
        elif nuevo:
            e.contraindicaciones_revisadas = bool(it.get("contraindicaciones_revisadas", False))

        if cambio and not nuevo:
            conteo["actualizados"] += 1

    en_bd_no_json = set(maquinas) - {m["codigo"] for m in datos["maquinas"]}
    for c in sorted(en_bd_no_json):
        informe.avisos.append(f"Máquina «{c}» está en la base pero no en el JSON (no se borra; desactívala con activa=false).")

    db.commit()
    return informe, conteo


def main() -> int:
    ap = argparse.ArgumentParser(description="Carga y valida el catálogo de Pulse Gym.")
    ap.add_argument("--validar", action="store_true", help="solo valida, no escribe en la base de datos")
    ap.add_argument("--estricto", action="store_true", help="las máquinas sin foto de referencia son un error")
    args = ap.parse_args()

    datos = leer_datos()
    if args.validar:
        informe, conteo = validar(datos, args.estricto), None
    else:
        from app.db.base import Base
        from app.db.session import SessionLocal, engine

        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            informe, conteo = cargar(db, datos, args.estricto)

    for a in informe.avisos:
        print("AVISO :", a)
    for e in informe.errores:
        print("ERROR :", e)
    r = informe.resumen
    print(f"\nCatálogo: {r['maquinas']} máquinas · {r['ejercicios']} ejercicios ({r['sin_equipo']} sin equipo) · "
          f"{r['grupos']} grupos · {r['zonas']} zonas de lesión")
    if not informe.ok:
        print("No se cargó nada: corrige los errores y vuelve a correr el script.")
        return 1
    if conteo is not None:
        print(f"Listo: {conteo['creados']} creados, {conteo['actualizados']} actualizados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
