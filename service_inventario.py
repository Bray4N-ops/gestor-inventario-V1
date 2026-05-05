import sqlite3 
from db import get_connection

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
    query = "SELECT * FROM productos WHERE 1=1"
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

def actualizar_producto(id_producto, nombre, categoria, cantidad, unidad, stock_minimo, lote, fecha_venc, ubicacion, notas):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE productos
        SET nombre = ?, categoria = ?, cantidad = ?, unidad = ?, stock_minimo = ?,
            lote = ?, fecha_vencimiento = ?, ubicacion = ?, notas = ?
        WHERE id = ?
    """, (nombre, categoria, cantidad, unidad, stock_minimo, lote, fecha_venc, ubicacion, notas, id_producto))
    conn.commit()
    conn.close()

def eliminar_producto(id_producto):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM movimientos WHERE producto_id = ?", (id_producto,))
    cursor.execute("DELETE FROM productos WHERE id = ?", (id_producto,))
    conn.commit()
    conn.close()

def registrar_movimiento(producto_id, tipo, cantidad, usuario='web', observacion=''):
    conn = get_connection()
    cursor = conn.cursor()
    if tipo == 'entrada':
        cursor.execute("UPDATE productos SET cantidad = cantidad + ? WHERE id = ?", (cantidad, producto_id))
    elif tipo == 'salida':
        cursor.execute("UPDATE productos SET cantidad = MAX(0, cantidad - ?) WHERE id = ?", (cantidad, producto_id))
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
    texto = texto.strip()
    if texto.isdigit():
        producto_id = int(texto)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos WHERE id = ?", (producto_id,))
        prod = cursor.fetchone()
        conn.close()
        if prod:
            return dict(prod)
    texto = texto.lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE LOWER(TRIM(nombre)) = ?", (texto,))
    producto = cursor.fetchone()
    if producto:
        conn.close()
        return dict(producto)
    cursor.execute("SELECT * FROM productos WHERE LOWER(nombre) LIKE ?", (f'%{texto}%',))
    resultados = cursor.fetchall()
    conn.close()
    if len(resultados) == 1:
        return dict(resultados[0])
    return None