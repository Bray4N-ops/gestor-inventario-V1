import ollama
import json
import re
import service_inventario as inventario

MODEL_NAME = "llama3.2:3b"  # o "llama3.2:7b" si lo descargaste

SYSTEM_PROMPT = """
Eres Leo, un asistente amable para gestionar un inventario rural.
Tu trabajo es ayudar al usuario a realizar acciones en el inventario. Puedes:
- Consultar el stock de un producto.
- Mostrar productos con stock bajo.
- Registrar entradas o salidas de productos.
- Agregar nuevos productos al sistema.

Para completar una acción, necesitas ciertos datos. Si falta alguno, se lo pides al usuario de manera clara y breve.
Cuando ya tengas toda la información necesaria, responde ÚNICAMENTE con un objeto JSON que represente la acción a ejecutar.
Si necesitas preguntar algo, simplemente haz la pregunta (sin JSON).

Las acciones disponibles son:
1. consultar_stock -> necesita "texto" (nombre o ID del producto).
2. listar_productos_bajos -> no necesita datos adicionales.
3. registrar_movimiento -> necesita "producto" (nombre o ID), "tipo" ("entrada" o "salida"), "cantidad" (número) y opcionalmente "observacion".
4. agregar_producto -> necesita "nombre", "categoria" (medicamento, alimento, herramienta, maquinaria), "cantidad", "unidad", "stock_minimo" y opcionales: "lote", "fecha_vencimiento", "ubicacion", "notas".

Ejemplo de conversación:
Usuario: "Añade 10 kg de Arroz Diana"
→ Ya tengo producto ("Arroz Diana"), tipo ("entrada"), cantidad (10). No necesito más. Respondo JSON: {"accion": "registrar_movimiento", "producto": "Arroz Diana", "tipo": "entrada", "cantidad": 10, "observacion": ""}

Usuario: "Quiero agregar un nuevo producto"
→ Me faltan todos los datos. Pregunto: "Claro, ¿cómo se llama el producto y de qué categoría es (medicamento, alimento, herramienta, maquinaria)?"
Luego el usuario responde y sigo preguntando hasta completar. Cuando tenga todo, genero el JSON.

Reglas:
- Siempre sé educado y directo.
- No inventes información. Si no entiendes algo, pregunta.
- Si el usuario no especifica algo (ej: stock mínimo), puedes proponer un valor típico o preguntar.
- Cuando vayas a ejecutar la acción, responde EXCLUSIVAMENTE con el JSON en una línea, sin rodeos.
"""

def interpretar_mensaje(texto_usuario, historial=None):
    """
    Envía el mensaje al modelo y devuelve la respuesta (texto o acción JSON).
    """
    # Construir el contexto con el historial (últimos 4 mensajes)
    prompt = SYSTEM_PROMPT + "\n"
    if historial:
        prompt += "Historial reciente:\n"
        for turno in historial[-4:]:
            prompt += f"Usuario: {turno['usuario']}\nAgente: {turno['respuesta']}\n"
    prompt += f"Usuario: {texto_usuario}\nAgente:"

    try:
        respuesta = ollama.generate(model=MODEL_NAME, prompt=prompt)
        texto = respuesta['response'].strip()
        return texto
    except Exception as e:
        return f"Error interno del modelo: {e}"

def ejecutar_accion(accion):
    """
    Ejecuta la acción JSON y devuelve un mensaje.
    """
    tipo = accion.get("accion")
    if tipo == "consultar_stock":
        texto = accion.get("texto", "").strip()
        if not texto:
            return "¿Qué producto te gustaría consultar?"
        prod = inventario.buscar_producto_flexible(texto)
        if prod:
            return f"📦 {prod['nombre']} (ID {prod['id']}): {prod['cantidad']} {prod['unidad']} | Stock mínimo: {prod['stock_minimo']} | Ubicación: {prod.get('ubicacion','No especificada')}"
        else:
            return f"No encontré ningún producto llamado '{texto}'. ¿Seguro que es el nombre correcto?"

    elif tipo == "listar_productos_bajos":
        productos = inventario.obtener_productos(solo_bajos=True)
        if not productos:
            return "✅ Todos los productos están sobre el nivel mínimo."
        resumen = "⚠️ Productos bajos de stock:\n"
        for p in productos:
            resumen += f"- {p['nombre']}: {p['cantidad']} {p['unidad']} (mínimo {p['stock_minimo']})\n"
        return resumen

    elif tipo == "registrar_movimiento":
        producto_ref = accion.get("producto", "").strip()
        tipo_mov = accion.get("tipo", "entrada")
        if tipo_mov not in ["entrada", "salida"]:
            return "El tipo debe ser 'entrada' o 'salida'."
        try:
            cantidad = float(accion.get("cantidad", 0))
        except (ValueError, TypeError):
            return "La cantidad debe ser un número. Ejemplo: 10."
        if cantidad <= 0:
            return "La cantidad debe ser mayor que cero."
        prod = inventario.buscar_producto_flexible(producto_ref)
        if not prod:
            return f"No encontré el producto '{producto_ref}'. Revisa el nombre o ID."
        obs = accion.get("observacion", "")
        inventario.registrar_movimiento(prod['id'], tipo_mov, cantidad, usuario="agente", observacion=obs)
        return f"✅ Movimiento registrado: {tipo_mov} de {cantidad} {prod['unidad']} de {prod['nombre']}."

    elif tipo == "agregar_producto":
        nombre = accion.get("nombre", "").strip()
        categoria = accion.get("categoria", "").strip()
        if not nombre or not categoria:
            return "Necesito al menos el nombre y la categoría para agregar un producto."
        if categoria not in ['medicamento','alimento','herramienta','maquinaria']:
            return f"Categoría '{categoria}' no válida. Debe ser: medicamento, alimento, herramienta, maquinaria."
        cantidad = float(accion.get("cantidad", 0))
        unidad = accion.get("unidad", "unidad")
        stock_minimo = int(accion.get("stock_minimo", 0))
        lote = accion.get("lote", "")
        fecha_venc = accion.get("fecha_vencimiento", "")
        ubicacion = accion.get("ubicacion", "")
        notas = accion.get("notas", "")
        inventario.agregar_producto(nombre, categoria, cantidad, unidad, stock_minimo, lote, fecha_venc, ubicacion, notas)
        return f"✅ Producto '{nombre}' agregado correctamente."

    else:
        return "No entiendo la acción solicitada. ¿Puedes reformularla?"

def procesar_mensaje(texto_usuario, historial=None):
    """
    Recibe el texto del usuario, llama al modelo, y si devuelve JSON ejecuta la acción,
    de lo contrario simplemente retorna la pregunta o respuesta del modelo.
    """
    respuesta_llm = interpretar_mensaje(texto_usuario, historial)
    
    # Intentar extraer un JSON de la respuesta
    json_match = re.search(r'\{.*?\}', respuesta_llm, re.DOTALL)
    if json_match:
        try:
            accion = json.loads(json_match.group())
            # Ejecutar la acción y obtener respuesta final
            resultado = ejecutar_accion(accion)
            return resultado
        except json.JSONDecodeError:
            pass  # no es un JSON válido, seguimos
    
    # Si no hay JSON, devolvemos la respuesta del modelo tal cual (pregunta, comentario, etc.)
    return respuesta_llm