"""Operaciones de texto compartidas por las reglas y los servicios."""
import unicodedata


def sin_tildes(t: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(ch) != "Mn")
