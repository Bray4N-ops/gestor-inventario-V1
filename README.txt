
  GESTOR DE INVENTARIO RURAL - Agente IA (NOT3S)


INSTRUCCIONES DE EJECUCIÓN

1. Activa el entorno virtual:
   - En Windows:  .\venv\Scripts\Activate.ps1   
   
2. Instala las dependencias necesarias (solo Flask por ahora):
   pip install flask

3. Asegúrate de que la base de datos SQLite se haya creado.
   Normalmente se crea automáticamente al iniciar la aplicación,
   pero si quieres hacerlo manualmente ejecuta:
   python db.py
   (Verás un mensaje "Base de datos creada exitosamente".)

4. Inicia el servidor web Flask:
   python app.py

5. Abre tu navegador web y ve a:
   http://localhost:5000

   También puedes acceder desde otros dispositivos en la misma red
   usando la IP de la máquina, por ejemplo:
   http://192.168.1.25:5000
   (La IP se muestra al iniciar el servidor en la terminal).

   Si quieres detener el servidor, presiona Ctrl+C en la terminal.

USO BÁSICO
----------
- Inventario: Ve todo los productos, filtra por categoría, busca por nombre.
- Agregar producto: Completa el formulario con los datos del nuevo ítem.
- Movimientos: Registra entradas y salidas rápidamente indicando el ID del producto.
- Alertas: Revisa qué productos están por debajo del stock mínimo configurado.

ESTRUCTURA DEL PROYECTO
-----------------------
gestor_inventario/
   app.py          -> Aplicación Flask (rutas y lógica de la web)
   db.py           -> Conexión y creación de la base de datos
   inventario.py   -> Funciones de negocio (CRUD de productos y movimientos)
   requirements.txt -> Lista de dependencias (opcional)
   static/
      style.css    -> Estilos CSS personalizados
   templates/
      base.html    -> Plantilla base con menú de navegación
      inventario.html
      agregar.html
      movimientos.html
      alertas.html

PRODUCCIÓN (opcional)
---------------------
Cuando quieras desplegarlo en un entorno real, usa un servidor más robusto.
Por ejemplo, con Waitress:
   pip install waitress
   waitress-serve --host 0.0.0.0 --port 5000 app:app

Para acceso desde internet necesitarás exponer el puerto (se recomienda
usar un proxy inverso como Nginx y HTTPS si es público).

NOTAS
-----
- Este sistema es la base del Agente IA not3s. Pronto podrás hablarle por
  Telegram o chat web para gestionar el inventario con lenguaje natural.
- Todos los datos se guardan en inventario.db (SQLite). Haz copias de
  seguridad periódicas si es necesario.
- Si encuentras algún error, verifica que todas las variables de entorno
  y archivos estén en la estructura correcta.

CONTACTO / SOPORTE
------------------
[<cruzhernandezbrayan68@gmail.com]