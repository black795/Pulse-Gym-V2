"""Traduce los errores de validación de FastAPI/Pydantic a mensajes en español claros para la app."""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

ETIQUETAS = {
    "nombre": "El nombre", "email": "El correo", "password": "La contraseña", "token": "El enlace",
    "edad": "La edad", "sexo": "El sexo", "altura_cm": "La altura", "peso_kg": "El peso",
    "grasa_pct": "El % de grasa", "masa_muscular_kg": "La masa muscular",
    "objetivo": "El objetivo", "nivel": "El nivel", "dias_por_semana": "Los días por semana",
    "minutos_por_sesion": "Los minutos por sesión", "descanso_default_seg": "El descanso",
    "zona": "La zona", "tipo": "El tipo", "estado": "El estado", "descripcion": "La descripción",
    "ubicacion": "La ubicación", "implementos": "La lista de implementos", "mancuernas_max_kg": "El peso máximo de mancuernas",
    "codigo": "La máquina", "origen": "El origen", "archivo": "El archivo de la foto",
}


def _num(v) -> str:
    """250.0 → "250" (los límites vienen como decimales cuando el campo es decimal)."""
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def _mensaje(err: dict) -> str:
    campo = str(err["loc"][-1]) if err.get("loc") else ""
    etiqueta = ETIQUETAS.get(campo, "Este dato")
    tipo = err.get("type", "")
    ctx = err.get("ctx") or {}

    if tipo == "missing":
        return f"{etiqueta} es obligatorio."
    if tipo in ("greater_than_equal", "greater_than"):
        return f"{etiqueta} debe ser al menos {_num(ctx.get('ge', ctx.get('gt')))}."
    if tipo in ("less_than_equal", "less_than"):
        return f"{etiqueta} debe ser como máximo {_num(ctx.get('le', ctx.get('lt')))}."
    if tipo == "string_too_short":
        return f"{etiqueta} es demasiado corto (mínimo {ctx.get('min_length')} caracteres)."
    if tipo == "string_too_long":
        return f"{etiqueta} es demasiado largo (máximo {ctx.get('max_length')} caracteres)."
    if tipo == "literal_error":
        return f"{etiqueta} tiene un valor no permitido."
    if tipo in ("int_parsing", "float_parsing", "int_from_float"):
        return f"{etiqueta} debe ser un número."
    if tipo == "extra_forbidden":
        return f"No se permite enviar «{campo}»."
    if campo == "email" or tipo == "value_error" and "email" in str(err.get("msg", "")).lower():
        return "El correo no es válido."
    if tipo == "value_error":  # validadores propios: el mensaje ya viene en español
        return str(err.get("msg", "")).removeprefix("Value error, ")
    return f"{etiqueta} no es válido."


async def manejar_validacion(_: Request, exc: RequestValidationError):
    errores = [{"campo": str(e["loc"][-1]) if e.get("loc") else "", "mensaje": _mensaje(e)} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"detail": errores[0]["mensaje"] if errores else "Datos no válidos.", "errores": errores},
    )
