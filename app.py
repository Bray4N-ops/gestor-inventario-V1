from flask import Flask, render_template, request, redirect, url_for, flash
from db import init_db
import service_inventario as inventario

app = Flask(__name__)
app.secret_key = 'clave-secreta-cambiar-en-produccion'  # Necesaria para flash messages

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
                           categorias=['todas','medicamento','alimento','herramienta','maquinaria'],
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
        
        if not nombre or categoria not in ['medicamento','alimento','herramienta','maquinaria']:
            flash('Nombre y categoría válida son obligatorios.', 'error')
            return redirect(url_for('agregar_producto_view'))
        
        inventario.agregar_producto(
            nombre, categoria, cantidad, unidad, stock_minimo,
            lote, fecha_venc, ubicacion, notas
        )
        flash('Producto agregado exitosamente', 'success')
        return redirect(url_for('inventario_view'))
    
    return render_template('agregar.html')

# ---- Editar producto (GET: formulario con los datos, POST: guarda cambios) ----
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

        if not nombre or categoria not in ['medicamento','alimento','herramienta','maquinaria']:
            flash('Nombre y categoría válida son obligatorios.', 'error')
            # Volvemos a mostrar el formulario con el producto
            return render_template('editar.html', producto=producto)

        inventario.actualizar_producto(
            id, nombre, categoria, cantidad, unidad, stock_minimo,
            lote, fecha_venc, ubicacion, notas
        )
        flash('Producto actualizado exitosamente', 'success')
        return redirect(url_for('inventario_view'))

    # Si es GET, mostramos formulario con los datos actuales
    return render_template('editar.html', producto=producto,
                           categorias=['medicamento','alimento','herramienta','maquinaria'])

# ---- Eliminar producto (borrado lógico) ----
@app.route('/producto/eliminar/<int:id>')
def eliminar_producto(id):
    inventario.eliminar_producto(id)
    flash('Producto eliminado correctamente', 'success')
    return redirect(url_for('inventario_view'))

# ---- Ruta para registrar un movimiento (viene por POST desde el formulario en inventario) ----
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

@app.route('/api/productos')
def api_productos():
    q = request.args.get('q', '')
    if len(q) < 1:
        return []
    productos = inventario.obtener_productos()  # función que devuelve lista de dicts
    sugerencias = [p for p in productos if q.lower() in p['nombre'].lower()]
    # Devolvemos solo id y nombre (y quizás unidad)
    return [{'id': p['id'], 'nombre': p['nombre'], 'unidad': p['unidad']} for p in sugerencias[:10]]

@app.context_processor
def utility_processor():
    return dict( service_inventario = inventario)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)