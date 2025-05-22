from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.Enum('Admin', 'Vendedor', 'Cliente'), default='Cliente')
    is_banned = db.Column(db.Boolean, default=False)
    licencias = db.relationship('Licencia', backref='usuario', lazy=True)
    tickets_creados = db.relationship('Ticket', foreign_keys='[Ticket.usuario_id_creador]', backref='creador', lazy=True)
    tickets_asignados = db.relationship('Ticket', foreign_keys='[Ticket.usuario_id_asignado]', backref='asignado', lazy=True)


    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Licencia(db.Model):
    __tablename__ = 'licencia'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.Enum('Mensual', 'Anual', 'Permanente'), nullable=False)
    precio = db.Column(db.Numeric(10,2), nullable=False)
    codigo = db.Column(db.String(50), unique=True)
    es_promocional = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.Date, nullable=False)
    fecha_inicio = db.Column(db.Date)
    fecha_fin = db.Column(db.Date)
    estado = db.Column(db.Enum('Stock', 'Activa', 'Suspendida', 'Expirada'), default='Stock')
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))

class Ticket(db.Model):
    __tablename__ = 'ticket'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion_inicial = db.Column(db.Text, nullable=False)
    prioridad = db.Column(db.Enum('Alta', 'Media', 'Baja'), default='Media')
    estado = db.Column(db.Enum('Abierto', 'En progreso', 'Cerrado'), default='Abierto')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_id_creador = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    usuario_id_asignado = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    mensajes = db.relationship('MensajeTicket', backref='ticket', lazy=True)

class MensajeTicket(db.Model):
    __tablename__ = 'mensajeticket'
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'))
    usuario_id_autor = db.Column(db.Integer, db.ForeignKey('usuario.id'))