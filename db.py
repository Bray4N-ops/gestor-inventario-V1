import sqlite3

def get_connection():
    conn = sqlite3.connect("inventario.db")
    conn.row_factory = sqlite3.Row  # Para acceder a columnas por nombre
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabla de productos (multicategoría)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL CHECK(categoria IN ('medicamento','alimento','herramienta','maquinaria')),
            cantidad REAL DEFAULT 0,
            unidad TEXT DEFAULT 'unidad',
            stock_minimo REAL DEFAULT 0,
            lote TEXT,
            fecha_vencimiento TEXT,
            ubicacion TEXT,
            notas TEXT,
            fecha_agregado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    #cursor.execute("ALTER TABLE productos ADD COLUMN activo INTEGER DEFAULT 1")
    
    # Tabla de movimientos (historial)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            tipo TEXT CHECK(tipo IN ('entrada','salida','ajuste')),
            cantidad REAL,
            usuario TEXT DEFAULT 'sistema',
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            observacion TEXT,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Base de datos creada exitosamente.")
