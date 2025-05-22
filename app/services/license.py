import random
import string
from app.extensions import db
from app.models.models import Licencia

def generar_codigo_licencia_unico():
    while True:
        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        if not Licencia.query.filter_by(codigo=codigo).first():
            return codigo

def get_licencia_activa(user):
    lic = Licencia.query.filter(
        Licencia.usuario_id == user.id,
        Licencia.estado == 'Activa'
    ).order_by(
        db.case(
            (Licencia.fecha_fin == None, 1), else_=0
        ),
        Licencia.fecha_fin.desc()
    ).first()
    return lic