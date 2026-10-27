from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import MAX_BYTES_PASSWORD


def validar_password(v: str) -> str:
    if len(v.encode("utf-8")) > MAX_BYTES_PASSWORD:
        raise ValueError("La contraseña es demasiado larga (máximo 72 caracteres).")
    if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
        raise ValueError("La contraseña debe tener al menos una letra y un número.")
    return v


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    email: str
    consentimiento_estado: Literal["pendiente", "aceptado", "rechazado"]
    perfil_completo: bool  # ¿ya puede generar su plan? (objetivo, nivel, días y minutos)
    created_at: datetime


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class RegistroIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validar_password(v)

    @field_validator("nombre")
    @classmethod
    def _nombre_limpio(cls, v: str) -> str:
        return " ".join(v.split())


class SesionOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_en_dias: int
    usuario: UsuarioOut


class RecuperarIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class RestablecerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validar_password(v)


class MensajeOut(BaseModel):
    mensaje: str
