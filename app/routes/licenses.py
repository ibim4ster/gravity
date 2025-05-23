from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date

from app.extensions import db
from app.models.models import Usuario, Licencia
from app.services.license import generar_codigo_licencia_unico

licenses = Blueprint('licenses', __name__, url_prefix='/licenses')

@licenses.route('/activate_paypal', methods=['POST'])
@login_required
def activar_licencia_paypal():
    data = request.get_json()
    tipo = data.get('tipo')
    if tipo not in ['Mensual', 'Anual', 'Permanente']:
        return jsonify(success=False, error="Tipo de licencia inválido"), 400

    # Desactivar licencias activas anteriores
    for lic in current_user.licencias:
        if lic.estado == 'Activa':
            lic.estado = 'Expirada'

    if tipo == 'Mensual':
        licencia = Licencia(
            tipo='Mensual',
            precio=9.99,
            fecha_creacion=date.today(),
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=30),
            estado='Activa',
            usuario_id=current_user.id,
            codigo=generar_codigo_licencia_unico()
        )
    elif tipo == 'Anual':
        hoy = date.today()
        try:
            fecha_fin = hoy.replace(year=hoy.year + 1)
        except ValueError:
            # Si hoy es 29 de febrero y el año siguiente no es bisiesto
            fecha_fin = hoy.replace(month=2, day=28, year=hoy.year + 1)
        licencia = Licencia(
            tipo='Anual',
            precio=99.99,
            fecha_creacion=hoy,
            fecha_inicio=hoy,
            fecha_fin=fecha_fin,  
            estado='Activa',
            usuario_id=current_user.id,
            codigo=generar_codigo_licencia_unico()
        )
    else:
        licencia = Licencia(
            tipo='Permanente',
            precio=299.99,
            fecha_creacion=date.today(),
            fecha_inicio=date.today(),
            fecha_fin=None,
            estado='Activa',
            usuario_id=current_user.id,
            codigo=generar_codigo_licencia_unico()
        )
    db.session.add(licencia)
    db.session.commit()
    return jsonify(success=True)

@licenses.route('/assign/<int:user_id>', methods=['POST'])
@login_required
def assign_license(user_id):
    if current_user.rol != 'Admin':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    user = Usuario.query.get_or_404(user_id)
    data = request.get_json()
    tipo = data.get('tipo')
    fecha_fin = data.get('fecha_fin')

    if not tipo:
        return jsonify({'success': False, 'error': 'Tipo de licencia requerido'}), 400

    # Define precios según el tipo de licencia
    if tipo == 'Mensual':
        precio = 9.99
    elif tipo == 'Anual':
        precio = 99.99
    elif tipo == 'Permanente':
        precio = 299.99
    else:
        precio = 0

    # Desactivar licencias activas anteriores
    for lic in user.licencias:
        if lic.estado == 'Activa':
            lic.estado = 'Expirada'

    # Crear la nueva licencia
    nueva_licencia = Licencia(
        tipo=tipo,
        precio=precio,
        fecha_creacion=datetime.now(),
        fecha_inicio=date.today(),
        estado='Activa',
        usuario_id=user.id,
        codigo=generar_codigo_licencia_unico()
    )

    if tipo != 'Permanente':
        try:
            nueva_licencia.fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except Exception:
            return jsonify({'success': False, 'error': 'Fecha de fin inválida'}), 400
    else:
        nueva_licencia.fecha_fin = None

    db.session.add(nueva_licencia)
    db.session.commit()
    return jsonify({'success': True})

@licenses.route('/compra_exitosa')
@login_required
def compra_exitosa():
    """Página de compra exitosa"""
    return render_template('compra_exitosa.html')

@licenses.route('/revoke/<int:user_id>', methods=['POST'])
@login_required
def revoke_license(user_id):
    if current_user.rol != 'Admin':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    user = Usuario.query.get_or_404(user_id)
    licencia = Licencia.query.filter_by(usuario_id=user.id, estado='Activa').first()
    if licencia:
        licencia.estado = 'Expirada'
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'No hay licencia activa'}), 404

@licenses.route('/panel')
@login_required
def licenses_panel():
    if current_user.rol != 'Admin':
        return "Acceso denegado", 403
    licencias = Licencia.query.order_by(Licencia.fecha_creacion.desc()).all()
    return render_template('licensespanel.html', licencias=licencias)

@licenses.route('/create', methods=['GET'])
@login_required
def create_license():
    if current_user.rol != 'Admin':
        return 'Acceso denegado', 403
    return render_template('create_license.html')

@licenses.route('/create', methods=['POST'])
@login_required
def create_license_post():
    if current_user.rol != 'Admin':
        return jsonify(success=False, error="Acceso denegado"), 403
    try:
        usuario_id_raw = request.form.get('usuario_id')
        usuario_id = int(usuario_id_raw) if usuario_id_raw else None
        tipo = request.form['tipo']
        estado = request.form['estado']
        fecha_inicio = datetime.strptime(request.form['fecha_inicio'], '%Y-%m-%d').date()
        fecha_fin = request.form.get('fecha_fin')
        if tipo != 'Permanente' and fecha_fin:
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        else:
            fecha_fin = None

        # Asigna el precio según el tipo de licencia
        if tipo == 'Mensual':
            precio = 9.99
        elif tipo == 'Anual':
            precio = 99.99
        elif tipo == 'Permanente':
            precio = 299.99
        else:
            precio = 0

        licencia = Licencia(
            usuario_id=usuario_id,
            tipo=tipo,
            precio=precio,
            estado=estado,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            fecha_creacion=datetime.now().date(),
            codigo=generar_codigo_licencia_unico()
        )
        db.session.add(licencia)
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500

@licenses.route('/edit/<int:license_id>')
@login_required
def edit_license(license_id):
    if current_user.rol != 'Admin':
        return 'Acceso denegado', 403
    licencia = Licencia.query.get_or_404(license_id)
    return render_template('edit_license.html', licencia=licencia)

@licenses.route('/update/<int:license_id>', methods=['POST'])
@login_required
def update_license(license_id):
    if current_user.rol != 'Admin':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error="Acceso denegado"), 403
        flash("Acceso denegado", "danger")
        return redirect(url_for('licenses.licenses_panel'))

    licencia = Licencia.query.get_or_404(license_id)
    try:
        licencia.tipo = request.form['tipo']
        licencia.estado = request.form['estado']
        licencia.fecha_inicio = datetime.strptime(request.form['fecha_inicio'], '%Y-%m-%d').date()
        if request.form['tipo'] != 'Permanente' and request.form.get('fecha_fin'):
            licencia.fecha_fin = datetime.strptime(request.form['fecha_fin'], '%Y-%m-%d').date()
        else:
            licencia.fecha_fin = None
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=True)
        flash("Licencia actualizada correctamente.", "success")
        return redirect(url_for('licenses.edit_license', license_id=license_id))
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error=str(e)), 500
        flash("Error al actualizar la licencia: " + str(e), "danger")
        return redirect(url_for('licenses.edit_license', license_id=license_id))

@licenses.route('/delete/<int:license_id>', methods=['POST'])
@login_required
def delete_license(license_id):
    if current_user.rol != 'Admin':
        return jsonify(success=False, error="Acceso denegado"), 403
    licencia = Licencia.query.get_or_404(license_id)
    db.session.delete(licencia)
    db.session.commit()
    return jsonify(success=True)

@licenses.route('/assign_stock/<int:license_id>', methods=['POST'])
@login_required
def assign_stock_license(license_id):
    if current_user.rol != 'Admin':
        return jsonify(success=False, error="Acceso denegado"), 403
    data = request.get_json()
    usuario_id = data.get('usuario_id')
    licencia = Licencia.query.get_or_404(license_id)
    if licencia.estado != 'Stock':
        return jsonify(success=False, error="La licencia no está en stock"), 400
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify(success=False, error="Usuario no encontrado"), 404
    # Desactivar licencias activas anteriores del usuario
    for lic in usuario.licencias:
        if lic.estado == 'Activa':
            lic.estado = 'Expirada'
    licencia.usuario_id = usuario.id
    licencia.estado = 'Activa'
    licencia.fecha_inicio = date.today()
    # Si no es permanente, pon fecha_fin a 30 días desde hoy
    if licencia.tipo == 'Mensual':
        licencia.fecha_fin = date.today() + timedelta(days=30)
    elif licencia.tipo == 'Anual':
        licencia.fecha_fin = date.today() + timedelta(days=365)
    else:
        licencia.fecha_fin = None
    db.session.commit()
    return jsonify(success=True)