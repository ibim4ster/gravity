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