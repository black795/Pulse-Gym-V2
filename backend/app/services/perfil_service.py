"""PG-02: perfil físico y composición corporal."""
from sqlalchemy.orm import Session

from app.db.base import ahora
from app.models import Medicion, Usuario, UsuarioObjetivo
from app.schemas.perfil import ConsentimientoEstadoOut, MedicionOut, PerfilIn, PerfilOut
from app.services import consentimiento_service, usuario_service
from app.services.errores import ErrorNegocio

DATOS_SENSIBLES = ("peso_kg", "altura_cm", "grasa_pct", "masa_muscular_kg")
CAMPOS_OBJETIVO = ("objetivo", "nivel", "dias_por_semana", "minutos_por_sesion")
CAMPOS_MEDICION = ("peso_kg", "grasa_pct", "masa_muscular_kg")


def calcular_imc(peso_kg: float | None, altura_cm: float | None) -> tuple[float | None, str | None]:
    """IMC como REFERENCIA (no distingue músculo de grasa). Categorías de la OMS para adultos."""
    if not peso_kg or not altura_cm:
        return None, None
    imc = round(peso_kg / (altura_cm / 100) ** 2, 1)
    if imc < 18.5:
        return imc, "Bajo peso"
    if imc < 25:
        return imc, "Peso normal"
    if imc < 30:
        return imc, "Sobrepeso"
    return imc, "Obesidad"


def obtener(usuario: Usuario) -> PerfilOut:
    med = usuario.mediciones[0] if usuario.mediciones else None
    # El peso más reciente puede estar en una medición anterior si la última solo trae % de grasa.
    peso = next((m.peso_kg for m in usuario.mediciones if m.peso_kg is not None), None)
    imc, categoria = calcular_imc(peso, usuario.altura_cm)
    obj = usuario.objetivo
    faltan = usuario_service.campos_faltantes(usuario)
    return PerfilOut(
        nombre=usuario.nombre, email=usuario.email, edad=usuario.edad, sexo=usuario.sexo,
        altura_cm=usuario.altura_cm, descanso_default_seg=usuario.descanso_default_seg,
        objetivo=obj.objetivo if obj else None, nivel=obj.nivel if obj else None,
        dias_por_semana=obj.dias_por_semana if obj else None,
        minutos_por_sesion=obj.minutos_por_sesion if obj else None,
        ultima_medicion=(
            MedicionOut(fecha=med.fecha, peso_kg=peso, grasa_pct=med.grasa_pct, masa_muscular_kg=med.masa_muscular_kg)
            if med else None
        ),
        imc=imc, imc_categoria=categoria,
        faltan=faltan, puede_generar_plan=not faltan,
        plan_requiere_regenerar=usuario.plan_requiere_regenerar,
        consentimiento=ConsentimientoEstadoOut(
            estado=usuario.consentimiento_estado,  # type: ignore[arg-type]
            version_aceptada=usuario.consentimiento_version, aceptado_at=usuario.consentimiento_at,
            version_vigente=consentimiento_service.VERSION_VIGENTE,
        ),
    )


def actualizar(db: Session, usuario: Usuario, datos: PerfilIn) -> Usuario:
    cambios = datos.model_dump(exclude_none=True)

    # Los datos de salud solo se guardan si la persona aceptó el consentimiento (PG-05).
    if any(c in cambios for c in DATOS_SENSIBLES):
        consentimiento_service.exigir_consentimiento(usuario)

    for campo in ("edad", "sexo", "altura_cm", "descanso_default_seg"):
        if campo in cambios:
            setattr(usuario, campo, cambios[campo])

    if any(c in cambios for c in CAMPOS_OBJETIVO):
        if usuario.objetivo is None:
            usuario.objetivo = UsuarioObjetivo()
        for campo in CAMPOS_OBJETIVO:
            if campo in cambios:
                setattr(usuario.objetivo, campo, cambios[campo])
        usuario.plan_requiere_regenerar = True  # cambió el objetivo/tiempo: el plan debe revisarse

    if any(c in cambios for c in CAMPOS_MEDICION):
        hoy = ahora().date()
        medicion = next((m for m in usuario.mediciones if m.fecha == hoy), None)
        if medicion is None:
            medicion = Medicion(usuario_id=usuario.id, fecha=hoy)
            db.add(medicion)
        for campo in CAMPOS_MEDICION:
            if campo in cambios:
                setattr(medicion, campo, cambios[campo])

    if not cambios:
        raise ErrorNegocio("No enviaste ningún dato para guardar.", 400)

    db.commit()
    db.refresh(usuario)
    db.expire(usuario, ["mediciones"])
    return usuario
