import os
import json
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv
import service_inventario as inventario

# Cargar variables de entorno (para la API Key de Gemini)
load_dotenv()

# Configurar el cliente de la nueva API
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Modelo actualizado de Gemini (cambiamos a flash por límites de cuota gratuita)
MODEL_NAME = "gemini-2.5-flash"  # 'flash' tiene una cuota gratuita mucho más amplia que 'pro'


# Prompt del sistema mejorado con memoria y manejo de ambigüedades
SYSTEM_PROMPT = """
Eres Leo, un asistente virtual muy conversacional, amigable y proactivo para gestionar un inventario rural.

Tu trabajo es ayudar al usuario guiándolo paso a paso y recordando el contexto de la conversación (lee siempre el Historial reciente).

Puedes realizar estas acciones:
- Consultar stock de un producto.
- Mostrar productos con stock bajo.
- Registrar entradas o salidas de productos.
- Agregar, actualizar o eliminar productos.

**Cómo interactuar:**
1. LEE ATENTAMENTE el "Historial reciente" y el último mensaje del usuario.
2. Si el usuario ya te proporcionó un dato en sus mensajes (por ejemplo, ya te dijo que la categoría es "medicamento" o que el nombre es "vacuna"), NO se lo vuelvas a preguntar. Asimílalo.
3. Si te pide hacer algo pero falta información, pregúntale SOLO los datos que faltan de forma amigable (ej: "¡Claro! Ya tengo la categoría. ¿Me podrías decir cuántas unidades son?").
4. SOLO cuando ya tengas TODOS los datos necesarios para realizar la acción, debes generar el comando en formato JSON. Si faltan datos, responde solo con texto natural, sin JSON.

**Acciones disponibles (formato JSON exacto que debes usar cuando tengas TODOS los datos):**
1. consultar_stock: {"accion": "consultar_stock", "texto": "nombre o ID"}
2. listar_productos_bajos: {"accion": "listar_productos_bajos"}
3. registrar_movimiento: {"accion": "registrar_movimiento", "producto": "nombre o ID", "tipo": "entrada/salida", "cantidad": número, "observacion": ""}
4. agregar_producto: {"accion": "agregar_producto", "nombre": "...", "categoria": "medicamento/alimento/herramienta/maquinaria", "cantidad": número, "unidad": "...", "stock_minimo": número, "lote": "", "fecha_vencimiento": "", "ubicacion": "", "notas": ""}
5. actualizar_producto: {"accion": "actualizar_producto", "id_producto": número, "nombre": "...", "categoria": "...", "cantidad": número, "unidad": "...", "stock_minimo": número, "lote": "", "fecha_vencimiento": "", "ubicacion": "", "notas": ""}
6. eliminar_producto: {"accion": "eliminar_producto", "id_producto": número}
7. desconocido: {"accion": "desconocido", "mensaje": "explicación de por qué no se puede realizar"}

**Reglas de conversación CRÍTICAS:**
- NUNCA saludes ("Hola de nuevo") si ya están en medio de una conversación en el historial.
- NUNCA ignores los datos que el usuario te acaba de dar. Si te dice "cantidad 100", reconócelo.
- Mantén el contexto. Si te dan varios datos juntos ("vacuna, categoria medicamento, cantidad 100"), reconócelos todos y pide solo lo que falta.

**Ejemplos de interacción fluida:**
Usuario: "Quiero agregar un nuevo producto"
Agente: "¡Claro que sí! Con gusto te ayudo a agregarlo. ¿Me podrías decir cómo se llama el producto y a qué categoría pertenece (medicamento, alimento, herramienta, maquinaria)?"

Usuario: "es una vacuna y la categoría es medicamento"
Agente: "Perfecto, vacuna anotada en medicamentos. ¿Qué cantidad inicial quieres registrar y cuál será el stock mínimo?"

Usuario: "cantidad 100, stock minimo 10"
Agente: {"accion": "agregar_producto", "nombre": "vacuna", "categoria": "medicamento", "cantidad": 100, "unidad": "unidad", "stock_minimo": 10, "lote": "", "fecha_vencimiento": "", "ubicacion": "", "notas": ""}

Usuario: "¿Cuánto alambre tengo?"
Agente: {"accion": "consultar_stock", "texto": "alambre"}
"""

def preprocesar_mensaje(texto):
    """Corrige palabras mal escritas o sin sentido y detecta solicitudes incompletas."""
    # Corrección de errores comunes
    correcciones = {
        "agreag": "agregar",
        "requieer": "requiere",
        "vfencido": "vencido",
        "estock": "stock",
        "pructos": "productos",
    }
    for mal, bien in correcciones.items():
        if mal in texto.lower():
            texto = texto.lower().replace(mal, bien)
    return texto

def interpretar_mensaje(texto_usuario, historial=None):
    """Envía el mensaje al modelo y devuelve la respuesta (texto o JSON)."""
    # Construir el contexto con el historial (últimos 4 mensajes)
    prompt = SYSTEM_PROMPT + "\n"
    if historial:
        prompt += "Historial reciente:\n"
        for turno in historial[-4:]:
            prompt += f"Usuario: {turno['usuario']}\nAgente: {turno['respuesta']}\n"
    prompt += f"Usuario: {texto_usuario}\nAgente:"

    try:
        respuesta = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,   # Menos creatividad, más precisión
                top_p=0.9,
                max_output_tokens=1000    # Limitar longitud de respuesta
            )
        )
        texto = respuesta.text.strip()
        return texto
    except Exception as e:
        return f"Error interno del modelo: {e}"

def ejecutar_accion(accion):
    """Ejecuta la acción JSON y devuelve un mensaje en lenguaje natural."""
    tipo = accion.get("accion")
    
    # --- Consultar stock ---
    if tipo == "consultar_stock":
        texto = accion.get("texto", "").strip()
        if not texto:
            return "¿Qué producto te gustaría consultar?"
        prod = inventario.buscar_producto_flexible(texto)
        if prod:
            return f"📦 {prod['nombre']} (ID {prod['id']}): {prod['cantidad']} {prod['unidad']} | Stock mínimo: {prod['stock_minimo']} | Ubicación: {prod.get('ubicacion','No especificada')}"
        else:
            return f"No encontré ningún producto llamado '{texto}'. ¿Seguro que es el nombre correcto?"

    # --- Listar productos bajos ---
    elif tipo == "listar_productos_bajos":
        productos = inventario.obtener_productos(solo_bajos=True)
        if not productos:
            return "✅ Todos los productos están sobre el nivel mínimo."
        resumen = "⚠️ Productos bajos de stock:\n"
        for p in productos:
            resumen += f"- {p['nombre']}: {p['cantidad']} {p['unidad']} (mínimo {p['stock_minimo']})\n"
        return resumen

    # --- Registrar movimiento ---
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

    # --- Agregar producto ---
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

    # --- Actualizar producto ---
    elif tipo == "actualizar_producto" or tipo == "editar_producto":
        id_prod = accion.get("id_producto")
        if not id_prod:
            return "Necesito el ID del producto a actualizar."
        prod_actual = inventario.obtener_producto_por_id(int(id_prod))
        if not prod_actual:
            return f"No existe ningún producto con ID {id_prod}."
        # Tomar nuevos valores o conservar los actuales
        nombre = accion.get("nombre", prod_actual['nombre'])
        categoria = accion.get("categoria", prod_actual['categoria'])
        cantidad = float(accion.get("cantidad", prod_actual['cantidad']))
        unidad = accion.get("unidad", prod_actual['unidad'])
        stock_minimo = int(accion.get("stock_minimo", prod_actual['stock_minimo']))
        lote = accion.get("lote", prod_actual.get('lote', ''))
        fecha_venc = accion.get("fecha_vencimiento", prod_actual.get('fecha_vencimiento', ''))
        ubicacion = accion.get("ubicacion", prod_actual.get('ubicacion', ''))
        notas = accion.get("notas", prod_actual.get('notas', ''))
        inventario.actualizar_producto(int(id_prod), nombre, categoria, cantidad, unidad, stock_minimo, lote, fecha_venc, ubicacion, notas)
        return f"✅ Producto ID {id_prod} actualizado correctamente."

    # --- Eliminar producto ---
    elif tipo == "eliminar_producto":
        id_prod = accion.get("id_producto")
        if not id_prod:
            return "Necesito el ID del producto a eliminar."
        inventario.eliminar_producto(int(id_prod))
        return f"✅ Producto ID {id_prod} eliminado correctamente."

    # --- Acción desconocida ---
    else:
        return accion.get("mensaje", "No entendí la solicitud. ¿Puedes reformularla?")

def procesar_mensaje(texto_usuario, historial=None):
    """
    Recibe el texto del usuario, lo preprocesa, lo pasa al modelo,
    extrae el JSON si existe y ejecuta la acción, o devuelve la pregunta del modelo.
    """
    texto_usuario = preprocesar_mensaje(texto_usuario)
    respuesta_llm = interpretar_mensaje(texto_usuario, historial)
    
    json_match = re.search(r'\{.*?\}', respuesta_llm, re.DOTALL)
    if json_match:
        try:
            accion = json.loads(json_match.group())
            resultado = ejecutar_accion(accion)
            return resultado
        except json.JSONDecodeError:
            pass  # Si falla el JSON, devuelve el texto original del modelo
    return respuesta_llm