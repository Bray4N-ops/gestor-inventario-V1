import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from db import init_db
import service_inventario as inventario
import agente_gemini as agente

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'clave-secreta-cambiar-en-produccion')

# Inicializar la base de datos al arrancar
init_db()

@app.route('/')
def index():
    return redirect(url_for('inventario_view'))

# ---- Ruta para ver inventario ----
@app.route('/inventario')
def inventario_view():
    filtro_cat = request.args.get('categoria', 'todas')
    busqueda = request.args.get('busqueda', '')
    solo_bajos = request.args.get('solo_bajos') == '1'

    if solo_bajos:
        productos = inventario.obtener_productos(solo_bajos=True)
    else:
        productos = inventario.obtener_productos(filtro_categoria=filtro_cat)

    # Filtro adicional por texto
    if busqueda:
        productos = [p for p in productos if busqueda.lower() in p['nombre'].lower()]

    return render_template('inventario.html',
                           productos=productos,
                           categorias=['todas', 'medicamento', 'alimento', 'herramienta', 'maquinaria'],
                           filtro_cat_actual=filtro_cat,
                           busqueda=busqueda)

# ---- Ruta para agregar producto (GET: formulario, POST: procesar) ----
@app.route('/agregar', methods=['GET', 'POST'])
def agregar_producto_view():
    if request.method == 'POST':
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        cantidad = float(request.form.get('cantidad', 0) or 0)
        unidad = request.form.get('unidad', 'unidad')
        stock_minimo = int(request.form.get('stock_minimo', 0) or 0)
        lote = request.form.get('lote', '')
        fecha_venc = request.form.get('fecha_vencimiento', '')
        ubicacion = request.form.get('ubicacion', '')
        notas = request.form.get('notas', '')

        if not nombre or categoria not in ['medicamento', 'alimento', 'herramienta', 'maquinaria']:
            flash('Nombre y categoría válida son obligatorios.', 'error')
            return redirect(url_for('agregar_producto_view'))

        inventario.agregar_producto(
            nombre, categoria, cantidad, unidad, stock_minimo,
            lote, fecha_venc, ubicacion, notas
        )
        flash('Producto agregado exitosamente', 'success')
        return redirect(url_for('inventario_view'))

    return render_template('agregar.html')

# ---- Editar producto ----
@app.route('/producto/editar/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    producto = inventario.obtener_producto_por_id(id)
    if not producto:
        flash('Producto no encontrado', 'error')
        return redirect(url_for('inventario_view'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        cantidad = float(request.form.get('cantidad', 0) or 0)
        unidad = request.form.get('unidad', 'unidad')
        stock_minimo = int(request.form.get('stock_minimo', 0) or 0)
        lote = request.form.get('lote', '')
        fecha_venc = request.form.get('fecha_vencimiento', '')
        ubicacion = request.form.get('ubicacion', '')
        notas = request.form.get('notas', '')

        if not nombre or categoria not in ['medicamento', 'alimento', 'herramienta', 'maquinaria']:
            flash('Nombre y categoría válida son obligatorios.', 'error')
            return render_template('editar.html', producto=producto,
                                   categorias=['medicamento', 'alimento', 'herramienta', 'maquinaria'])

        inventario.actualizar_producto(
            id, nombre, categoria, cantidad, unidad, stock_minimo,
            lote, fecha_venc, ubicacion, notas
        )
        flash('Producto actualizado exitosamente', 'success')
        return redirect(url_for('inventario_view'))

    return render_template('editar.html', producto=producto,
                           categorias=['medicamento', 'alimento', 'herramienta', 'maquinaria'])

# ---- Eliminar producto ----
@app.route('/producto/eliminar/<int:id>')
def eliminar_producto(id):
    inventario.eliminar_producto(id)
    flash('Producto eliminado correctamente', 'success')
    return redirect(url_for('inventario_view'))

# ---- Ruta para registrar un movimiento (viene por POST del formulario en inventario) ----
@app.route('/movimiento', methods=['POST'])
def registrar_movimiento_view():
    producto_id = int(request.form['producto_id'])
    tipo = request.form['tipo']
    cantidad = float(request.form['cantidad'])
    observacion = request.form.get('observacion', '')

    if tipo not in ['entrada', 'salida']:
        flash('Tipo de movimiento inválido', 'error')
        return redirect(url_for('inventario_view'))

    inventario.registrar_movimiento(producto_id, tipo, cantidad, usuario='web', observacion=observacion)
    flash(f'Movimiento de {tipo} por {cantidad} registrado', 'success')
    return redirect(url_for('inventario_view'))

# ---- Ruta para ver movimientos ----
@app.route('/movimientos')
def movimientos_view():
    movs = inventario.obtener_movimientos()
    return render_template('movimientos.html', movimientos=movs)

# ---- Ruta para alertas (productos por debajo del mínimo) ----
@app.route('/alertas')
def alertas_view():
    bajos = inventario.obtener_productos(solo_bajos=True)
    return render_template('alertas.html', productos=bajos)

# ---- API para autocompletado ----
@app.route('/api/productos')
def api_productos():
    q = request.args.get('q', '')
    if len(q) < 1:
        return jsonify([])
    productos = inventario.obtener_productos()
    sugerencias = [p for p in productos if q.lower() in p['nombre'].lower()]
    return jsonify([{'id': p['id'], 'nombre': p['nombre'], 'unidad': p['unidad']} for p in sugerencias[:10]])

# ---- Chat con el agente IA ----
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    # Inicializar historial si no existe en la sesión
    if 'historial' not in session:
        session['historial'] = []

    respuesta = None
    if request.method == 'POST':
        mensaje = request.form.get('mensaje', '').strip()
        if mensaje:
            historial = session['historial']  # lista de dicts {'usuario': texto, 'respuesta': texto}
            respuesta = agente.procesar_mensaje(mensaje, historial=historial)
            # Guardar interacción
            historial.append({'usuario': mensaje, 'respuesta': respuesta})
            # Mantener solo los últimos 10 mensajes
            if len(historial) > 10:
                session['historial'] = historial[-10:]
            else:
                session['historial'] = historial
            session.modified = True

    return render_template('chat.html', respuesta=respuesta, historial=session.get('historial', []))

# ---- Contexto para plantillas ----
@app.context_processor
def utility_processor():
    return dict(service_inventario=inventario)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)