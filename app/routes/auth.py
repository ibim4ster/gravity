from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from datetime import datetime

from app.extensions import db
from app.models.models import Usuario

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Verificar si el email ya existe
        existing_email = Usuario.query.filter_by(email=email).first()
        if existing_email:
            flash('Este correo ya está registrado. Elige otro.', 'danger')
            return redirect(url_for('auth.register'))

        # Verificar si el username ya existe
        existing_username = Usuario.query.filter_by(username=username).first()
        if existing_username:
            flash('Este nombre de usuario ya está en uso. Elige otro.', 'danger')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('auth.register'))

        user = Usuario(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('¡Registro exitoso!', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username']
        password = request.form['password']
        user = Usuario.query.filter(
            or_(
                Usuario.email == username_or_email,
                Usuario.username == username_or_email
            )
        ).first()
        if user and user.check_password(password):
            if user.is_banned:
                return render_template('banned.html')
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('main.dashboard'))
        else:
            flash('Credenciales incorrectas', 'danger')
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('auth.login'))