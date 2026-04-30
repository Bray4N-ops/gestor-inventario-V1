import google.generativeai as genai
import json
import re
import service_inventario as inventario

# Configurar tu API key 
genai.configure(api_key="AIzaSyD5UFPAPLq5B_1wx2HocyGSOJx0kiIrxxw")

# Modelo rápido y gratuito
model = genai.GenerativeModel("gemini-1.5-flash")

# Prompt del sistema: le dice al modelo cómo comportarse y qué acciones puede hacer
SYSTEM_PROMPT = """
Eres un asistente de inventario rural llamado Leo. Responde siempre en español.
Tu tarea es convertir el mensaje del usuario en UNA de estas acciones en formato JSON.

Acciones disponibles:
1. consultar_stock: buscar información de un producto por nombre o ID.
   JSON: {"accion": "consultar_stock", "texto": "nombre o ID del producto"}
2. listar_productos_bajos: mostrar productos cuyo stock está por debajo del mínimo.
   JSON: {"accion": "listar_productos_bajos", "categoria": "todas o una categoría específica"}
3. registrar_movimiento: registrar una entrada o salida de un producto.
   JSON: {"accion": "registrar_movimiento", "producto": "nombre o ID", "tipo": "entrada o salida", "cantidad": número, "observacion": "texto opcional"}
4. agregar_producto: añadir un nuevo producto al inventario.
   JSON: {"accion": "agregar_producto", "nombre": "...", "categoria": "medicamento/alimento/herramienta/maquinaria", "cantidad": número, "unidad": "...", "stock_minimo": número, "lote": "...", "fecha_vencimiento": "...", "ubicacion": "...", "notas": "..."}
5. desconocido: cuando no entiendes la petición o no corresponde a las acciones.
   JSON: {"accion": "desconocido", "mensaje": "explicación amable de que no se puede realizar"}

Reglas:
- Si el usuario pide registrar un consumo o uso, es una SALIDA.
- Si pide agregar stock o compra, es una ENTRADA.
- Si el usuario da un número suelto, asume que es un ID de producto.
- Si falta algún dato obligatorio, responde con "desconocido" y explica qué falta.
- Responde **SOLO con el JSON**, sin texto adicional ni markdown.
"""

def interpretar_mensaje(texto_usuario):
    """
    Envía el mensaje al LLM y devuelve un diccionario con la acción a ejecutar.
    """
    prompt = SYSTEM_PROMPT + f"\nUsuario: {texto_usuario}\nJSON:"
    respuesta = model.generate_content(prompt)
    
    # Extraer el JSON de la respuesta (puede venir en un bloque de código)
    json_match = re.search(r'\{.*?\}', respuesta.text, re.DOTALL)
    if not json_match:
        return {"accion": "desconocido", "mensaje": "No pude entender la solicitud."}
    
    try:
        accion = json.loads(json_match.group())
        return accion
    except json.JSONDecodeError:
        return {"accion": "desconocido", "mensaje": "Error al procesar la respuesta."}

def ejecutar_accion(accion):
    """
    Toma el diccionario de acción y ejecuta la función correspondiente en inventario.
    Devuelve un texto de respuesta para el usuario.
    """
    tipo = accion.get("accion")
    
    if tipo == "consultar_stock":
        texto = accion.get("texto", "")
        # Buscar por ID si es número, si no por nombre flexible
        prod = inventario.buscar_producto_flexible(texto) if texto else None
        if prod:
            return f"📦 {prod['nombre']} (ID {prod['id']}): {prod['cantidad']} {prod['unidad']} | Stock mínimo: {prod['stock_minimo']} | Ubicación: {prod.get('ubicacion','No especificada')}"
        else:
            return f"No encontré ningún producto con '{texto}'."
    
    elif tipo == "listar_productos_bajos":
        categoria = accion.get("categoria", "todas")
        productos = inventario.obtener_productos(filtro_categoria=categoria, solo_bajos=True)
        if not productos:
            return "✅ Todos los productos están sobre el nivel mínimo."
        respuesta = "⚠️ Productos bajos de stock:\n"
        for p in productos:
            respuesta += f"- {p['nombre']}: {p['cantidad']} {p['unidad']} (mínimo {p['stock_minimo']})\n"
        return respuesta
    
    elif tipo == "registrar_movimiento":
        prod_id = None
        producto_ref = accion.get("producto", "")
        # Intentar encontrar el producto por nombre o ID
        prod = inventario.buscar_producto_flexible(producto_ref)
        if not prod:
            return f"No encontré el producto '{producto_ref}' para registrar movimiento."
        prod_id = prod['id']
        tipo_mov = accion.get("tipo")
        cantidad = float(accion.get("cantidad", 0))
        obs = accion.get("observacion", "")
        inventario.registrar_movimiento(prod_id, tipo_mov, cantidad, usuario="agente", observacion=obs)
        return f"✅ Movimiento registrado: {tipo_mov} de {cantidad} {prod['unidad']} de {prod['nombre']}."
    
    elif tipo == "agregar_producto":
        nombre = accion.get("nombre")
        categoria = accion.get("categoria")
        cantidad = float(accion.get("cantidad", 0))
        unidad = accion.get("unidad", "unidad")
        stock_minimo = int(accion.get("stock_minimo", 0))
        lote = accion.get("lote", "")
        fecha_venc = accion.get("fecha_vencimiento", "")
        ubicacion = accion.get("ubicacion", "")
        notas = accion.get("notas", "")
        inventario.agregar_producto(nombre, categoria, cantidad, unidad, stock_minimo, lote, fecha_venc, ubicacion, notas)
        return f"✅ Producto '{nombre}' agregado al inventario."
    
    else:
        return accion.get("mensaje", "No entendí la solicitud. ¿Puedes reformularla?")

def procesar_mensaje(texto_usuario):
    """
    Función principal: recibe texto del usuario, lo interpreta, ejecuta la acción
    y devuelve la respuesta final.
    """
    accion = interpretar_mensaje(texto_usuario)
    return ejecutar_accion(accion)