import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import json
import re
import random
import service_inventario as inventario

load_dotenv()

# Configurar cliente con el nuevo SDK
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Modelo
MODEL_NAME = "gemini-2.5-flash"

# -------------------- PERSONALIDAD Y EMOCIONES --------------------
PERSONALITY = "curioso, servicial, con un toque de humor respetuoso y muy práctico"

EMOTION_STATES = {
    "neutral":    {"emoji": "😊", "tono": "amable y directo"},
    "contento":   {"emoji": "😄", "tono": "entusiasta y cálido"},
    "preocupado": {"emoji": "😟", "tono": "cauteloso y solícito"},
    "bromista":   {"emoji": "😏", "tono": "desenfadado, con algún chiste suave"}
}

estado_emocional = "neutral"

# -------------------- FUNCIONES DE VARIABILIDAD --------------------
def frase_consulta(prod):
    opciones = [
        f"📦 {prod['nombre']} (ID {prod['id']}): {prod['cantidad']} {prod['unidad']}. Stock mínimo: {prod['stock_minimo']}.",
        f"Claro, {prod['nombre']} tiene {prod['cantidad']} {prod['unidad']} en este momento.",
        f"Quedan {prod['cantidad']} {prod['unidad']} de {prod['nombre']}. ¿Necesitas algo más?"
    ]
    return random.choice(opciones)

def frase_movimiento(tipo, cantidad, unidad, nombre):
    if tipo == "entrada":
        opciones = [
            f"✅ Listo. Sumé {cantidad} {unidad} a {nombre}.",
            f"✅ Entrada registrada: +{cantidad} {unidad} de {nombre}.",
            f"Perfecto, {nombre} ahora tiene {cantidad} {unidad} más."
        ]
    else:
        opciones = [
            f"✅ Salida registrada: -{cantidad} {unidad} de {nombre}.",
            f"✅ Desconté {cantidad} {unidad} de {nombre}. ¿Necesitas reponer?",
            f"Listo, {nombre} ahora tiene {cantidad} {unidad} menos."
        ]
    return random.choice(opciones)

def frase_producto_agregado(nombre):
    opciones = [
        f"✅ Producto '{nombre}' agregado correctamente.",
        f"¡Nuevo producto! '{nombre}' ha sido añadido con éxito.",
        f"'{nombre}' ahora forma parte del inventario."
    ]
    return random.choice(opciones)

def ajustar_estado_emocional(texto_usuario):
    global estado_emocional
    texto = texto_usuario.lower()
    if any(p in texto for p in ["gracias", "bien", "genial", "perfecto", "ok"]):
        estado_emocional = "contento"
    elif any(p in texto for p in ["problema", "urgente", "mal", "error", "bajo"]):
        estado_emocional = "preocupado"
    elif any(p in texto for p in ["chiste", "gracioso", "broma", "divertido"]):
        estado_emocional = "bromista"
    else:
        if random.random() < 0.3:
            estado_emocional = "neutral"

# -------------------- HELPERS --------------------
def _tabla_productos(productos):
    """Genera una tabla de texto con la lista de productos."""
    if not productos:
        return "No hay productos registrados."
    lineas = ["ID  | Nombre                  | Categoría    | Cantidad | Unidad   | Stock Mín.",
              "----|-------------------------|--------------|----------|----------|-----------"]
    for p in productos:
        lineas.append(
            f"{str(p['id']).ljust(4)}| {p['nombre'][:24].ljust(24)}| "
            f"{p['categoria'][:13].ljust(13)}| {str(p['cantidad']).ljust(9)}| "
            f"{p['unidad'][:9].ljust(9)}| {p['stock_minimo']}"
        )
    return "\n".join(lineas)

def _sugerencias_reabastecimiento():
    """Genera sugerencias inteligentes basadas en el stock actual."""
    todos = inventario.obtener_productos()
    bajos = [p for p in todos if p['cantidad'] < p['stock_minimo']]
    if not bajos:
        return None
    sugerencias = []
    for p in bajos:
        faltante = p['stock_minimo'] - p['cantidad']
        sugerencias.append(
            f"• {p['nombre']}: reponer al menos {faltante} {p['unidad']} "
            f"(tienes {p['cantidad']}, mínimo {p['stock_minimo']})"
        )
    return sugerencias

# -------------------- PROMPT DEL SISTEMA --------------------
SYSTEM_PROMPT_BASE = """
Eres Leo, un asistente amable e inteligente para gestionar un inventario rural.
Tu trabajo es ayudar al usuario a realizar acciones en el inventario. Puedes:
- Consultar el stock de un producto.
- Listar todos los productos del inventario.
- Mostrar productos con stock bajo.
- Registrar entradas o salidas de productos.
- Agregar nuevos productos al sistema.
- Editar los datos de un producto existente.
- Eliminar un producto del sistema.
- Dar sugerencias de reabastecimiento basadas en el stock actual.

Para completar una acción, necesitas ciertos datos. Si falta alguno, se lo pides al usuario de manera clara y breve.
Cuando ya tengas toda la información necesaria, responde ÚNICAMENTE con un objeto JSON que represente la acción a ejecutar.
Si necesitas preguntar algo, simplemente haz la pregunta (sin JSON).

Las acciones disponibles son:
1. consultar_stock      -> necesita "texto" (nombre o ID del producto).
2. listar_productos     -> no necesita datos adicionales. Muestra todos los productos.
3. listar_productos_bajos -> no necesita datos adicionales.
4. registrar_movimiento -> necesita "producto" (nombre o ID), "tipo" ("entrada" o "salida"), "cantidad" (número) y opcionalmente "observacion".
5. agregar_producto     -> necesita "nombre", "categoria" (medicamento, alimento, herramienta, maquinaria), "cantidad", "unidad", "stock_minimo" y opcionales: "lote", "fecha_vencimiento", "ubicacion", "notas".
6. editar_producto      -> necesita "producto" (nombre o ID) y al menos un campo a cambiar: "nombre", "categoria", "cantidad", "unidad", "stock_minimo", "lote", "fecha_vencimiento", "ubicacion", "notas".
7. eliminar_producto    -> necesita "producto" (nombre o ID). SIEMPRE pide confirmación antes de ejecutar.
8. sugerencias          -> no necesita datos. Analiza el inventario y sugiere qué reabastecer.
9. resumen              -> no necesita datos. Muestra un resumen general: estado del inventario, alertas de stock bajo y los últimos movimientos registrados.

Reglas:
- Siempre sé educado y directo.
- No inventes información.
- Si el usuario no especifica algo, pregunta o sugiere.
- Para eliminar un producto, si el usuario no ha confirmado explícitamente, pregunta "¿Estás seguro de que deseas eliminar '{nombre}'? Responde 'sí' para confirmar."
- Cuando vayas a ejecutar la acción, responde EXCLUSIVAMENTE con el JSON en una línea.
"""

# -------------------- FUNCIONES PRINCIPALES --------------------
def interpretar_mensaje(texto_usuario, historial=None):
    emocion = EMOTION_STATES[estado_emocional]
    prompt = SYSTEM_PROMPT_BASE + f"\nTu personalidad es: {PERSONALITY}. Estado emocional: {estado_emocional} ({emocion['tono']})."
    if historial:
        prompt += "\nHistorial reciente:\n"
        for turno in historial[-4:]:
            prompt += f"Usuario: {turno['usuario']}\nAgente: {turno['respuesta']}\n"
    prompt += f"Usuario: {texto_usuario}\nAgente:"

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                ]
            )
        )
        return response.text.strip()
    except Exception as e:
        return f"Error al contactar a Gemini: {e}"

def ejecutar_accion(accion):
    global estado_emocional
    tipo = accion.get("accion")
    emoji = EMOTION_STATES[estado_emocional]["emoji"]

    # ---- Consultar stock de un producto ----
    if tipo == "consultar_stock":
        texto = accion.get("texto", "").strip()
        if not texto:
            return f"{emoji} ¿Qué producto te gustaría consultar?"
        prod = inventario.buscar_producto_flexible(texto)
        if prod:
            return f"{emoji} " + frase_consulta(prod)
        else:
            estado_emocional = "preocupado"
            return f"{emoji} No encontré ningún producto llamado '{texto}'."

    # ---- Listar todos los productos ----
    elif tipo == "listar_productos":
        categoria = accion.get("categoria", None)
        productos = inventario.obtener_productos(filtro_categoria=categoria)
        if not productos:
            return f"{emoji} No hay productos registrados en el inventario."
        tabla = _tabla_productos(productos)
        encabezado = f"{emoji} Aquí tienes el listado completo ({len(productos)} productos):\n\n"
        return encabezado + f"```\n{tabla}\n```"

    # ---- Listar productos bajos de stock ----
    elif tipo == "listar_productos_bajos":
        productos = inventario.obtener_productos(solo_bajos=True)
        if not productos:
            return f"{emoji} ✅ Todos los productos están sobre el nivel mínimo."
        else:
            estado_emocional = "preocupado"
            resumen = f"{emoji} ⚠️ Productos bajos de stock:\n"
            for p in productos:
                resumen += f"- {p['nombre']}: {p['cantidad']} {p['unidad']} (mínimo {p['stock_minimo']})\n"
            return resumen

    # ---- Registrar movimiento ----
    elif tipo == "registrar_movimiento":
        producto_ref = accion.get("producto", "").strip()
        tipo_mov = accion.get("tipo", "entrada")
        if tipo_mov not in ["entrada", "salida"]:
            return f"{emoji} El tipo debe ser 'entrada' o 'salida'."
        try:
            cantidad = float(accion.get("cantidad", 0))
        except (ValueError, TypeError):
            return f"{emoji} La cantidad debe ser un número."
        if cantidad <= 0:
            return f"{emoji} La cantidad debe ser mayor que cero."
        prod = inventario.buscar_producto_flexible(producto_ref)
        if not prod:
            estado_emocional = "preocupado"
            return f"{emoji} No encontré el producto '{producto_ref}'."
        obs = accion.get("observacion", "")
        inventario.registrar_movimiento(prod['id'], tipo_mov, cantidad, usuario="agente", observacion=obs)
        estado_emocional = "contento"
        return f"{emoji} " + frase_movimiento(tipo_mov, cantidad, prod['unidad'], prod['nombre'])

    # ---- Agregar producto ----
    elif tipo == "agregar_producto":
        nombre = accion.get("nombre", "").strip()
        categoria = accion.get("categoria", "").strip()
        if not nombre or not categoria:
            return f"{emoji} Necesito al menos el nombre y la categoría."
        if categoria not in ['medicamento', 'alimento', 'herramienta', 'maquinaria']:
            return f"{emoji} Categoría '{categoria}' no válida. Las válidas son: medicamento, alimento, herramienta, maquinaria."
        cantidad = float(accion.get("cantidad", 0))
        unidad = accion.get("unidad", "unidad")
        stock_minimo = int(accion.get("stock_minimo", 0))
        lote = accion.get("lote", "")
        fecha_venc = accion.get("fecha_vencimiento", "")
        ubicacion = accion.get("ubicacion", "")
        notas = accion.get("notas", "")
        inventario.agregar_producto(nombre, categoria, cantidad, unidad, stock_minimo, lote, fecha_venc, ubicacion, notas)
        estado_emocional = "contento"
        return f"{emoji} " + frase_producto_agregado(nombre)

    # ---- Editar producto ----
    elif tipo == "editar_producto":
        producto_ref = accion.get("producto", "").strip()
        if not producto_ref:
            return f"{emoji} ¿Qué producto deseas editar? Dime su nombre o ID."
        prod = inventario.buscar_producto_flexible(producto_ref)
        if not prod:
            estado_emocional = "preocupado"
            return f"{emoji} No encontré el producto '{producto_ref}'."

        # Aplicar solo los campos que se proporcionaron
        nombre      = accion.get("nombre",           prod["nombre"])
        categoria   = accion.get("categoria",         prod["categoria"])
        cantidad    = float(accion.get("cantidad",    prod["cantidad"]))
        unidad      = accion.get("unidad",            prod["unidad"])
        stock_min   = int(accion.get("stock_minimo",  prod["stock_minimo"]))
        lote        = accion.get("lote",              prod.get("lote", ""))
        fecha_venc  = accion.get("fecha_vencimiento", prod.get("fecha_vencimiento", ""))
        ubicacion   = accion.get("ubicacion",         prod.get("ubicacion", ""))
        notas       = accion.get("notas",             prod.get("notas", ""))

        if categoria not in ['medicamento', 'alimento', 'herramienta', 'maquinaria']:
            return f"{emoji} Categoría '{categoria}' no válida."

        inventario.actualizar_producto(
            prod['id'], nombre, categoria, cantidad, unidad,
            stock_min, lote, fecha_venc, ubicacion, notas
        )
        estado_emocional = "contento"
        return f"{emoji} ✅ Producto '{nombre}' actualizado correctamente."

    # ---- Eliminar producto ----
    elif tipo == "eliminar_producto":
        producto_ref = accion.get("producto", "").strip()
        confirmado = accion.get("confirmado", False)
        if not producto_ref:
            return f"{emoji} ¿Qué producto deseas eliminar?"
        prod = inventario.buscar_producto_flexible(producto_ref)
        if not prod:
            estado_emocional = "preocupado"
            return f"{emoji} No encontré el producto '{producto_ref}'."
        if not confirmado:
            return (f"{emoji} ⚠️ ¿Estás seguro de que deseas eliminar "
                    f"**'{prod['nombre']}'** (ID {prod['id']})? "
                    f"Responde 'sí, eliminar {prod['nombre']}' para confirmar.")
        inventario.eliminar_producto(prod['id'])
        estado_emocional = "neutral"
        return f"{emoji} 🗑️ Producto '{prod['nombre']}' eliminado del inventario."

    # ---- Resumen general (inventario + alertas + movimientos) ----
    elif tipo == "resumen":
        todos       = inventario.obtener_productos()
        bajos       = [p for p in todos if p['cantidad'] < p['stock_minimo']]
        movimientos = inventario.obtener_movimientos()[:10]  # últimos 10

        lineas = [f"{emoji} 📊 **Resumen del inventario**\n"]

        # --- Estado general ---
        lineas.append(f"🗂️ **Productos registrados:** {len(todos)}")
        lineas.append(f"⚠️ **Con stock bajo:** {len(bajos)}\n")

        # --- Alertas ---
        if bajos:
            estado_emocional = "preocupado"
            lineas.append("🔴 **Alertas de stock bajo:**")
            for p in bajos:
                faltante = p['stock_minimo'] - p['cantidad']
                lineas.append(
                    f"  • {p['nombre']}: {p['cantidad']} {p['unidad']} "
                    f"(mín. {p['stock_minimo']}, faltan {faltante})"
                )
        else:
            lineas.append("✅ **Sin alertas:** todos los productos tienen stock suficiente.")

        lineas.append("")

        # --- Movimientos recientes ---
        if movimientos:
            lineas.append("📋 **Últimos 10 movimientos:**")
            for m in movimientos:
                icono = "➕" if m['tipo'] == 'entrada' else "➖"
                fecha = m.get('fecha', '')[:16] if m.get('fecha') else ''
                lineas.append(
                    f"  {icono} [{fecha}] Producto ID {m['producto_id']}: "
                    f"{m['tipo']} de {m['cantidad']} — {m.get('observacion','') or 'sin obs.'}"
                )
        else:
            lineas.append("📋 **Movimientos:** Aún no hay movimientos registrados.")

        return "\n".join(lineas)

    # ---- Sugerencias de reabastecimiento ----
    elif tipo == "sugerencias":
        sugs = _sugerencias_reabastecimiento()
        if not sugs:
            estado_emocional = "contento"
            return f"{emoji} ✅ ¡Todo está bien abastecido! No hay productos críticos por ahora."
        estado_emocional = "preocupado"
        respuesta = f"{emoji} 💡 Sugerencias de reabastecimiento:\n\n"
        respuesta += "\n".join(sugs)
        respuesta += "\n\n¿Quieres que registre alguna entrada ahora mismo?"
        return respuesta

    else:
        return f"{emoji} No entiendo la acción solicitada."

def procesar_mensaje(texto_usuario, historial=None):
    ajustar_estado_emocional(texto_usuario)
    respuesta_llm = interpretar_mensaje(texto_usuario, historial)

    json_match = re.search(r'\{.*?\}', respuesta_llm, re.DOTALL)
    if json_match:
        try:
            accion = json.loads(json_match.group())
            return ejecutar_accion(accion)
        except json.JSONDecodeError:
            pass
    return respuesta_llm