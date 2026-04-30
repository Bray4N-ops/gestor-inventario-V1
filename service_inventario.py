import sqlite3 
from db import get_connection #viene de tu archivo db.py y sirve para abrir la conexión a la base de datos.

def buscar_producto_flexible(texto):
    texto = texto.strip()
    # Si el texto es un número entero, buscar por ID
    if texto.isdigit():
        producto_id = int(texto)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos WHERE id = ?", (producto_id,))
        prod = cursor.fetchone()
        conn.close()
        if prod:
            return dict(prod)
    # ... resto de la función (pasar a minúsculas, etc.)

def agregar_producto(nombre, categoria, cantidad=0, unidad='unidad', stock_minimo=0, lote=None, fecha_vencimiento=None, ubicacion=None, notas=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO productos (nombre, categoria, cantidad, unidad, stock_minimo, lote, fecha_vencimiento, ubicacion, notas)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nombre, categoria, cantidad, unidad, stock_minimo, lote, fecha_vencimiento, ubicacion, notas))
    conn.commit()
    conn.close()

def obtener_productos(filtro_categoria=None, solo_bajos=False):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM productos WHERE activo = 1"
    params = []
    if filtro_categoria and filtro_categoria != 'todas':
        query += " AND categoria = ?"
        params.append(filtro_categoria)
    if solo_bajos:
        query += " AND cantidad < stock_minimo"
    cursor.execute(query, params)
    productos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return productos

def obtener_producto_por_id(producto_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE id = ?", (producto_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def actualizar_cantidad(producto_id, cantidad_nueva):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE productos SET cantidad = ? WHERE id = ?", (cantidad_nueva, producto_id))
    conn.commit()
    conn.close()

def registrar_movimiento(producto_id, tipo, cantidad, usuario='web', observacion=''):
    conn = get_connection()
    cursor = conn.cursor()
    # Actualizar stock según tipo
    if tipo == 'entrada':
        cursor.execute("UPDATE productos SET cantidad = cantidad + ? WHERE id = ?", (cantidad, producto_id))
    elif tipo == 'salida':
        cursor.execute("UPDATE productos SET cantidad = MAX(0, cantidad - ?) WHERE id = ?", (cantidad, producto_id))
    # Insertar el movimiento
    cursor.execute('''
        INSERT INTO movimientos (producto_id, tipo, cantidad, usuario, observacion)
        VALUES (?, ?, ?, ?, ?)
    ''', (producto_id, tipo, cantidad, usuario, observacion))
    conn.commit()
    conn.close()

def obtener_movimientos(producto_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if producto_id:
        cursor.execute("SELECT * FROM movimientos WHERE producto_id = ? ORDER BY fecha DESC", (producto_id,))
    else:
        cursor.execute("SELECT * FROM movimientos ORDER BY fecha DESC LIMIT 100")
    movs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return movs

def buscar_producto_flexible(texto):
    """Busca un producto por coincidencia insensible a mayúsculas/minúsculas y espacios.
    Retorna el producto si encuentra uno solo, o None."""
    texto = texto.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    # Primero intenta igualdad exacta sin importar capitalización
    cursor.execute("SELECT * FROM productos WHERE LOWER(TRIM(nombre)) = ?", (texto,))
    producto = cursor.fetchone()
    if producto:
        conn.close()
        return dict(producto)
    
    
    # Si no, busca productos que contengan el texto
    cursor.execute("SELECT * FROM productos WHERE LOWER(nombre) LIKE ?", (f'%{texto}%',))
    resultados = cursor.fetchall()
    conn.close()
    if len(resultados) == 1:
        return dict(resultados[0])
    return None

def actualizar_producto(id_producto, nombre, categoria, cantidad, unidad,
                        stock_minimo, lote, fecha_venc, ubicacion, notas):
    """Actualiza todos los campos de un producto existente."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE productos
        SET nombre = ?,
            categoria = ?,
            cantidad = ?,
            unidad = ?,
            stock_minimo = ?,
            lote = ?,
            fecha_vencimiento = ?,
            ubicacion = ?,
            notas = ?
        WHERE id = ?
    """, (nombre, categoria, cantidad, unidad, stock_minimo, lote,
          fecha_venc, ubicacion, notas, id_producto))
    conn.commit()
    conn.close()

def eliminar_producto(id_producto):
    """Borra lógicamente el producto (campo activo = 0)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE productos SET activo = 0 WHERE id = ?", (id_producto,))
    conn.commit()
    conn.close()