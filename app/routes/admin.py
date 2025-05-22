from flask import Blueprint, render_template, request, redirect, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models.models import Usuario
from app.services.license import get_licencia_activa

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/')
@login_required
def admin_panel():
    if current_user.rol != 'Admin':
        return 'Acceso denegado', 403
    users = Usuario.query.all()
    return render_template('admin_panel.html', users=users)

@admin.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.rol != 'Admin':
        return 'Acceso denegado', 403
    user = Usuario.query.get_or_404(user_id)
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_rol = request.form.get('rol')
        ban_status = request.form.get('ban_status')
        if new_username:
            user.username = new_username
        if new_rol:
            user.rol = new_rol
        user.is_banned = (ban_status == '1')
        db.session.commit()
        return redirect('/admin')
    return render_template('edit_user.html', user=user)

@admin.route('/update_user/<int:user_id>', methods=['POST'])
@login_required
def update_user(user_id):
    if current_user.rol != 'Admin':
        return 'Acceso denegado', 403
    user = Usuario.query.get_or_404(user_id)
    if user:
        username = request.form.get('username')
        rol = request.form.get('rol')
        banned_status = request.form.get('banned') == '1'
        user.email = username  # Si tienes username como campo, cámbialo aquí
        user.rol = rol
        user.is_banned = banned_status
        db.session.commit()
        return jsonify(success=True)
    return jsonify(success=False, error='Usuario no encontrado'), 404

@admin.route('/delete_user/<int:user_id>', methods=['DELETE', 'POST'])
@login_required
def delete_user(user_id):
    if current_user.rol != 'Admin':
        return jsonify(success=False, error="Acceso denegado"), 403
    user = Usuario.query.get(user_id)
    if not user:
        return jsonify(success=False, error="Usuario no encontrado"), 404
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error="Error interno del servidor"), 500