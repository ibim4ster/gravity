from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
import subprocess
import os
from flask import Response, jsonify
import logging

from app.config import Config
from app.services.license import get_licencia_activa
from app.services.search import (
    buscar_por_numero, buscar_por_id_facebook, 
    buscar_por_nombre, buscar_por_apellido, 
    buscar_por_ciudad
)

search = Blueprint('search', __name__, url_prefix='/search')

@search.route('/', methods=['GET', 'POST'])
@login_required
def buscar():
    licencia = get_licencia_activa(current_user)
    if not licencia:
        return redirect(url_for('main.dashboard'))
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

@search.route('/sherlock')
@login_required
def sherlock():
    return render_template('sherlock.html')

@search.route('/run_sherlock', methods=['POST'])
@login_required
def run_sherlock():
    username = request.json.get('username')
    if not username:
        return jsonify({'message': 'No username provided!'}), 400
    try:
        process = subprocess.Popen(
            ['python', Config.SHERLOCK_PATH, username],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(Config.SHERLOCK_PATH)
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