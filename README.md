# 📦 Sistema de Inventario Rural con IA

Sistema web de gestión de inventario para uso rural, con agente inteligente **Leo** powered by Google Gemini.

---

## ✨ Características

- **Inventario completo**: agrega, edita, elimina y consulta productos.
- **Categorías**: medicamentos, alimentos, herramientas, maquinaria.
- **Movimientos**: registra entradas y salidas de stock con historial.
- **Alertas**: detecta automáticamente productos bajo el stock mínimo.
- **Agente Leo (IA)**: chat inteligente con Gemini que puede:
  - Consultar stock de un producto
  - Listar todos los productos del inventario
  - Mostrar productos con stock bajo
  - Registrar entradas y salidas
  - Agregar nuevos productos
  - Editar datos de un producto
  - Eliminar un producto (con confirmación)
  - Dar sugerencias de reabastecimiento
- **Interacción por Voz**:
  - Dictado de comandos e interacción mediante el micrófono del dispositivo (Speech-to-Text).
  - Respuestas en audio, con lectura automática en voz alta de los mensajes del Agente Leo (Text-to-Speech).

---

## 🚀 Instalación y ejecución

### 1. Clona el repositorio

```bash
git clone <URL_del_repo>
cd inventario
```

### 2. Crea y activa el entorno virtual

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Instala las dependencias

```bash
pip install -r requirements.txt
```

### 4. Configura las variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
GEMINI_API_KEY=tu_api_key_de_google_gemini
FLASK_SECRET_KEY=una_clave_secreta_aleatoria
```

> Obtén tu API key en: https://aistudio.google.com/app/apikey

### 5. Ejecuta la aplicación

```powershell
.\venv\Scripts\python.exe app.py
```

La aplicación estará disponible en: **http://127.0.0.1:5000**

---

## 📁 Estructura del proyecto

```
inventario/
├── app.py                 # Aplicación Flask principal (rutas web)
├── agente_gemini.py       # Agente Leo (IA con Gemini)
├── service_inventario.py  # Lógica de negocio e interfaz con la BD
├── db.py                  # Conexión y creación de la base de datos
├── inventario.db          # Base de datos SQLite (generada automáticamente)
├── requirements.txt       # Dependencias del proyecto
├── .env                   # Variables de entorno (NO subir a Git)
├── .gitignore
├── templates/             # Plantillas HTML (Jinja2)
│   ├── inventario.html
│   ├── agregar.html
│   ├── editar.html
│   ├── movimientos.html
│   ├── alertas.html
│   └── chat.html
└── static/                # Archivos estáticos (CSS, JS, imágenes)
```

---

## 🤖 Cómo usar al agente Leo

Accede a la sección **Chat** en la app. Puedes escribirle de forma natural o utilizar el botón del **micrófono 🎙️** para dictar tus órdenes por voz. Además, Leo te leerá sus respuestas automáticamente (puedes detener el audio con el botón 🔇). Ejemplos:

| Acción | Ejemplo de mensaje |
|---|---|
| Ver todos los productos | "muéstrame el inventario completo" |
| Consultar stock | "¿cuánto hay de paracetamol?" |
| Agregar producto | "agrega 50 kg de maíz como alimento" |
| Registrar entrada | "entraron 20 unidades de jeringa" |
| Registrar salida | "salieron 5 litros de gasolina" |
| Editar producto | "cambia el stock mínimo del maíz a 10" |
| Eliminar producto | "elimina el producto jeringa" |
| Ver stock bajo | "¿qué productos están por agotarse?" |
| Sugerencias | "¿qué necesito reabastecer?" |

---

## 🛠️ Stack tecnológico

- **Backend**: Python 3.13 + Flask 3.x
- **Base de datos**: SQLite 3
- **IA**: Google Gemini (`gemini-2.5-flash`) via `google-genai` SDK
- **Frontend**: HTML5 + Jinja2 + CSS

---

## ⚠️ Notas de seguridad

- Nunca subas el archivo `.env` a Git (ya está en `.gitignore`).
- En producción, usa un servidor WSGI como **Gunicorn** en lugar del servidor de desarrollo de Flask.