# app.py (refactorizado para models-4tablas.py)
import string
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
from sqlalchemy import or_

import logging
import requests
import subprocess
import os

from models import db, Usuario, Licencia, Ticket, MensajeTicket

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://test:test@127.0.0.1/gravitytest'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

with app.app_context():
    db.create_all()

# ========== LOGIN MANAGER ==========
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ========== REGISTRO ==========
@app.route('/register', methods=['GET', 'POST'])
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
            return redirect(url_for('register'))

        # Verificar si el username ya existe
        existing_username = Usuario.query.filter_by(username=username).first()
        if existing_username:
            flash('Este nombre de usuario ya está en uso. Elige otro.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('register'))

        user = Usuario(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('¡Registro exitoso!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# ========== LOGIN ==========
@app.route('/login', methods=['GET', 'POST'])
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
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas', 'danger')
    return render_template('login.html')

# ========== LOGOUT ==========
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

# ========== START PAGE ==========
@app.route('/')
def start_page():
    return render_template('start_page.html')

# ========== DASHBOARD ==========
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', section='dashboard', Licencia=Licencia)

# ========== COMPRAR LICENCIA ==========
@app.route('/comprar', methods=['GET', 'POST'])
@login_required
def comprar():
    if request.method == 'POST':
        return redirect(url_for('compra_exitosa'))
    return render_template('comprar_content.html')

@app.route('/compra_exitosa', methods=['GET'])
def compra_exitosa():
    return render_template('compra_exitosa.html')

# ========== ACTIVAR LICENCIA PAYPAL ==========
@app.route('/activar_licencia_paypal', methods=['POST'])
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
            precio=99.99,
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

# ========== CONFIGURACIÓN DE USUARIO ==========
@app.route('/update_configuration', methods=['POST'])
@login_required
def update_configuration():
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    if not new_password or not confirm_password:
        flash('Ambos campos de contraseña son obligatorios.', 'danger')
        return redirect(request.referrer)
    if new_password != confirm_password:
        flash('Las contraseñas no coinciden.', 'danger')
        return redirect(request.referrer)
    user = current_user
    user.set_password(new_password)
    db.session.commit()
    flash('Tu contraseña ha sido actualizada con éxito. Por favor, inicia sesión de nuevo.', 'success')
    logout_user()
    return redirect(url_for('login'))

@app.route('/eliminar_cuenta', methods=['POST'])
@login_required
def eliminar_cuenta():
    user_id = current_user.id
    user = Usuario.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        logout_user()
        flash('Tu cuenta ha sido eliminada con éxito.', 'success')
    else:
        flash('No se pudo encontrar tu cuenta. Por favor, intenta de nuevo.', 'danger')
    return redirect(url_for('login'))

# ========== BÚSQUEDA DE USUARIOS ==========
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

@app.route('/buscar', methods=['GET', 'POST'])
@login_required
def buscar():
    licencia = get_licencia_activa(current_user)
    if not licencia:
        return redirect(url_for('dashboard'))
    resultados = []
    if request.method == 'POST':
        criterio = request.form.get('criterio')
        termino = request.form.get('termino')
        archivo = 'txt/spain.txt'
        if criterio == 'Teléfono':
            resultados = buscar_por_numero(archivo, termino)
        elif criterio == 'Facebook ID':
            resultados = buscar_por_id_facebook(archivo, termino)
        elif criterio == 'Nombre':
            resultados = buscar_por_nombre(archivo, termino)
        elif criterio == 'Apellido':
            resultados = buscar_por_apellido(archivo, termino)
        elif criterio == 'Ciudad/Pais':
            resultados = buscar_por_ciudad(archivo, termino)
    return render_template('resultados.html', resultados=resultados)

def buscar_por_numero(archivo, numero_parcial):
    resultados = []
    with open(archivo, 'r', encoding='utf-8') as file:
        for linea in file:
            datos = linea.strip().split(':')
            if len(datos) > 0:
                numero = datos[0]
                if numero_parcial in numero:
                    ciudad = datos[5] if len(datos) > 5 else ''
                    localidad = datos[6] if len(datos) > 6 else ''
                    ciudad_completa = f"{ciudad}, {localidad}".strip(', ')
                    resultados.append({
                        "numero": numero,
                        "id_facebook": datos[1],
                        "nombre": datos[2],
                        "apellido": datos[3],
                        "genero": datos[4],
                        "ciudad": ciudad_completa
                    })
    return resultados

def buscar_por_id_facebook(archivo, id_buscar):
    resultados = []
    with open(archivo, 'r', encoding='utf-8') as file:
        for linea in file:
            datos = linea.strip().split(':')
            if len(datos) > 1:
                id_facebook = datos[1]
                if id_facebook == id_buscar:
                    ciudad = datos[5] if len(datos) > 5 else ''
                    localidad = datos[6] if len(datos) > 6 else ''
                    ciudad_completa = f"{ciudad}, {localidad}".strip(', ')
                    resultados.append({
                        "numero": datos[0],
                        "id_facebook": id_facebook,
                        "nombre": datos[2],
                        "apellido": datos[3],
                        "genero": datos[4],
                        "ciudad": ciudad_completa
                    })
    return resultados

def buscar_por_nombre(archivo, nombre_buscar):
    resultados = []
    with open(archivo, 'r', encoding='utf-8') as file:
        for linea in file:
            datos = linea.strip().split(':')
            if len(datos) > 3:
                ciudad = datos[5] if len(datos) > 5 else ''
                localidad = datos[6] if len(datos) > 6 else ''
                ciudad_completa = f"{ciudad}, {localidad}".strip(', ')
                nombre_completo = datos[2] + " " + datos[3]
                if nombre_buscar.lower() in nombre_completo.lower():
                    resultados.append({
                        "numero": datos[0],
                        "id_facebook": datos[1],
                        "nombre": datos[2],
                        "apellido": datos[3],
                        "genero": datos[4],
                        "ciudad": ciudad_completa
                    })
    return resultados

def buscar_por_apellido(archivo, apellido_buscar):
    resultados = []
    with open(archivo, 'r', encoding='utf-8') as file:
        for linea in file:
            datos = linea.strip().split(':')
            if len(datos) > 3:
                ciudad = datos[5] if len(datos) > 5 else ''
                localidad = datos[6] if len(datos) > 6 else ''
                ciudad_completa = f"{ciudad}, {localidad}".strip(', ')
                apellido = " ".join(datos[3:5])
                if apellido_buscar.lower() in apellido.lower():
                    resultados.append({
                        "numero": datos[0],
                        "id_facebook": datos[1],
                        "nombre": datos[2],
                        "apellido": apellido,
                        "genero": datos[4],
                        "ciudad": ciudad_completa
                    })
    return resultados

def buscar_por_ciudad(archivo, ciudad_buscar):
    resultados = []
    with open(archivo, 'r', encoding='utf-8') as file:
        for linea in file:
            datos = linea.strip().split(':')
            if len(datos) > 5 and datos[5]:
                ciudad = datos[5]
                localidad = datos[6] if len(datos) > 6 else ''
                ciudad_completa = f"{ciudad}, {localidad}".strip(', ')
                if ciudad_buscar.lower() in ciudad_completa.lower():
                    resultados.append({
                        "numero": datos[0],
                        "id_facebook": datos[1],
                        "nombre": datos[2],
                        "apellido": datos[3],
                        "genero": datos[4],
                        "ciudad": ciudad_completa
                    })
    return resultados

# ========== CONTENIDO DINÁMICO ==========
@app.route('/get_content/<path:section>')
@login_required
def get_content(section):
    if section == 'dashboard':
        return render_template('dashboard_content.html')
    elif section == 'comprar':
        return render_template('comprar_content.html')
    elif section == 'buscar':
        return render_template('index.html')
    elif section == 'sherlock':
        return render_template('sherlock.html')
    elif section == 'configuracion':
        return render_template('configuracion_content.html', user=current_user)
    elif section == 'adminpanel':
        if current_user.rol != 'Admin':
            return 'Acceso denegado', 403
        users = Usuario.query.all()
        return render_template('admin_panel.html', users=users)
    elif section.startswith('edit_user/'):
        user_id = int(section.split('/')[-1])
        user = Usuario.query.get_or_404(user_id)
        return render_template('edit_user.html', user=user)
    else:
        return 'Sección no encontrada', 404

# ========== ADMIN PANEL ==========
@app.route('/adminpanel')
@login_required
def admin_panel():
    if current_user.rol != 'Admin':
        return 'Acceso denegado', 403
    users = Usuario.query.all()
    return render_template('admin_panel.html', users=users)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
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
            user.username = new_username  # <-- Cambia aquí
        if new_rol:
            user.rol = new_rol
        user.is_banned = (ban_status == '1')
        db.session.commit()
        return redirect('/adminpanel')
    return render_template('edit_user.html', user=user)

@app.route('/update_user/<int:user_id>', methods=['POST'])
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

@app.route('/delete_user/<int:user_id>', methods=['DELETE', 'POST'])
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

# ========== LICENCIAS ==========
# ========== ASIGNAR LICENCIA ==========
@app.route('/assign_license/<int:user_id>', methods=['POST'])
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
        precio = 49.99
    elif tipo == 'Permanente':
        precio = 99.99
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

def generar_codigo_licencia_unico():
    import random, string
    while True:
        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        if not Licencia.query.filter_by(codigo=codigo).first():
            return codigo
        
# ========== QUITAR LICENCIA A USUARIO ==========        
@app.route('/revoke_license/<int:user_id>', methods=['POST'])
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
    
# ========== MOSTRAR LICENCIAS DEL PANEL DE LICENCIAS ==========
@app.route('/get_content/licensespanel')
@login_required
def licenses_panel():
    if current_user.rol != 'Admin':
        return "Acceso denegado", 403
    licencias = Licencia.query.order_by(Licencia.fecha_creacion.desc()).all()
    return render_template('licensespanel.html', licencias=licencias)

# ========== NUEVA RUTA PARA CREAR LICENCIA DESDE LICENSES.HTML ==========
@app.route('/get_content/create_license')
@login_required
def create_license():
    if current_user.rol != 'Admin':
        return 'Acceso denegado', 403
    return render_template('create_license.html')

# ========== RUTA PARA CREAR LICENCIA DESDE CREATE_LICENSE.HTML ==========
@app.route('/create_license', methods=['POST'])
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
            precio = 49.99
        elif tipo == 'Permanente':
            precio = 99.99
        else:
            precio = 0

        licencia = Licencia(
            usuario_id=usuario_id,
            tipo=tipo,
            precio=precio,  # <-- ¡Aquí añades el precio!
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
        
# ========== NUEVA RUTA PARA EDITAR LICENCIA ==========
@app.route('/get_content/edit_license/<int:license_id>')
@login_required
def edit_license(license_id):
    if current_user.rol != 'Admin':
        return 'Acceso denegado', 403
    licencia = Licencia.query.get_or_404(license_id)
    return render_template('edit_license.html', licencia=licencia)

# ========== RUTA PARA ACTUALIZAR LICENCIA DESDE EDIT_LICENSE.HTML ==========
@app.route('/update_license/<int:license_id>', methods=['POST'])
@login_required
def update_license(license_id):
    if current_user.rol != 'Admin':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error="Acceso denegado"), 403
        flash("Acceso denegado", "danger")
        return redirect(url_for('licenses_panel'))

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
        return redirect(url_for('edit_license', license_id=license_id))
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error=str(e)), 500
        flash("Error al actualizar la licencia: " + str(e), "danger")
        return redirect(url_for('edit_license', license_id=license_id))
    
# ========== RUTA PARA ELIMINAR LICENCIA  DESDE EDIT_LICENSE.HTML ==========
@app.route('/delete_license/<int:license_id>', methods=['POST'])
@login_required
def delete_license(license_id):
    if current_user.rol != 'Admin':
        return jsonify(success=False, error="Acceso denegado"), 403
    licencia = Licencia.query.get_or_404(license_id)
    db.session.delete(licencia)
    db.session.commit()
    return jsonify(success=True)

# ========== ASIGNAR LICENCIA EN STOCK A UN USUARIO DESDE EDIT_LICENSE.HTML ==========
@app.route('/assign_stock_license/<int:license_id>', methods=['POST'])
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

# ========== SHERLOCK ==========
SHERLOCK_PATH = r"G:\Dam2\testSherlock\sherlock-master\sherlock_project\sherlock.py"

@app.route('/sherlock')
@login_required
def sherlock():
    return render_template('sherlock.html')

@app.route('/run_sherlock', methods=['POST'])
@login_required
def run_sherlock():
    username = request.json.get('username')
    if not username:
        return jsonify({'message': 'No username provided!'}), 400
    try:
        process = subprocess.Popen(
            ['python', SHERLOCK_PATH, username],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(SHERLOCK_PATH)
        )
        def generate_sherlock_output():
            for line in iter(process.stdout.readline, ''):
                yield f"data: {line.strip()}\n\n"
            process.stdout.close()
            process.wait()
            yield "data: Sherlock ha terminado.\n\n"
        return Response(generate_sherlock_output(), content_type='text/event-stream')
    except Exception as e:
        logging.error(f"Error al ejecutar Sherlock: {str(e)}")
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500

if __name__ == '__main__':
    app.run(debug=True)