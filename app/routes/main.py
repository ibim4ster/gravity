from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.models.models import Licencia, Usuario

main = Blueprint('main', __name__)

@main.route('/')
def start_page():
    return render_template('start_page.html')

@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', section='dashboard', Licencia=Licencia)

@main.route('/get_content/<path:section>')
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
    elif section == 'licensespanel':
        if current_user.rol != 'Admin':
            return 'Acceso denegado', 403
        from app.models.models import Licencia
        licencias = Licencia.query.order_by(Licencia.fecha_creacion.desc()).all()
        return render_template('licensespanel.html', licencias=licencias)
    elif section == 'create_license':  
        if current_user.rol != 'Admin':
            return 'Acceso denegado', 403
        return render_template('create_license.html')
    elif section.startswith('edit_license/'):
        if current_user.rol != 'Admin':
            return 'Acceso denegado', 403
        from app.models.models import Licencia  # Añadir esta línea
        license_id = int(section.split('/')[-1])
        licencia = Licencia.query.get_or_404(license_id)
        return render_template('edit_license.html', licencia=licencia)
    elif section.startswith('edit_user/'):
        user_id = int(section.split('/')[-1])
        user = Usuario.query.get_or_404(user_id)
        return render_template('edit_user.html', user=user)
    else:
        return 'Sección no encontrada', 404

# Importación dentro de la función para evitar errores de importación circular
@main.route('/comprar', methods=['GET', 'POST'])
@login_required
def comprar():
    from flask import redirect, url_for, request
    if request.method == 'POST':
        return redirect(url_for('main.compra_exitosa'))
    return render_template('comprar_content.html')
