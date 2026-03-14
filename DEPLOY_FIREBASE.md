# Desplegar Taller Loro: Firebase (web) + Backend (Python)

Tu sitio tiene dos partes:

1. **Frontend (HTML/CSS)** → Firebase Hosting (ya lo hiciste).
2. **Backend (Flask, base de datos, correos)** → Render o Railway.

Así la página queda pública en Internet y el formulario de citas sigue funcionando (guardado en BD y envío de correos).

---

## 1. Contenido en `public/` para Firebase

En la carpeta **`public/`** deben estar todos los archivos que quieres que se sirvan en la URL de Firebase:

- `index.html`
- `mecanica.html`
- `alquiler.html`
- `style.css`
- `404.html` (opcional)

Si cambias algo en los HTML/CSS de la raíz del proyecto, copia los cambios a `public/` antes de hacer deploy.

---

## 2. Subir solo la web a Firebase

En la terminal, dentro de la carpeta del proyecto:

```bash
firebase deploy --only hosting
```

O solo:

```bash
firebase deploy
```

Tu sitio quedará en una URL como:

- `https://TU-PROYECTO.web.app`
- `https://TU-PROYECTO.firebaseapp.com`

Ahí tendrás Inicio, Mecánica y Alquiler. El **formulario de citas no guardará nada ni enviará correos** hasta que tengas el backend desplegado y configurado (paso 4).

---

## 3. Desplegar el backend (Flask) en Render

Para que las citas se guarden y se envíen los correos:

1. Sube el proyecto a **GitHub** (incluyendo `app.py`, `requirements.txt`, y la carpeta `public/` si quieres; Render solo necesita el backend).

2. En [Render](https://render.com):
   - **New → Web Service**
   - Conecta el repositorio de GitHub.
   - Configuración sugerida:
     - **Build command:** `pip install -r requirements.txt`
     - **Start command:** `waitress-serve --listen=0.0.0.0:$PORT app:app`
   - En **Environment** añade las variables para el correo (y opcionalmente la BD):
     - `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`, `EMAIL_PASSWORD`, etc.

3. Render te dará una URL del backend, por ejemplo:
   - `https://taller-loro-api.onrender.com`

---

## 4. Conectar el formulario (Firebase) con el backend (Render)

Cuando tengas la URL del backend (ej: `https://taller-loro-api.onrender.com`):

1. En **`public/index.html`** busca la etiqueta:
   ```html
   <meta name="api-base" content="" id="api-base">
   ```

2. Pon la URL del backend (sin barra final):
   ```html
   <meta name="api-base" content="https://taller-loro-api.onrender.com" id="api-base">
   ```

3. Vuelve a desplegar en Firebase:
   ```bash
   firebase deploy --only hosting
   ```

A partir de ahí, cuando alguien envíe el formulario desde tu sitio en Firebase, el navegador enviará los datos a tu app en Render; allí se guardará la cita en la base de datos y se enviará el correo de confirmación.

---

## 5. Resumen de URLs

| Dónde        | URL ejemplo                          |
|-------------|--------------------------------------|
| Sitio web   | `https://TU-PROYECTO.web.app`        |
| API citas   | `https://taller-loro-api.onrender.com/api/citas` |

El formulario usa `api-base` + `/api/citas` para enviar los datos al backend.

---

## 6. Nota sobre la base de datos

En Render, el sistema de archivos no es persistente. Si usas SQLite (`taller.db`), se borrará al reiniciar el servicio. Para producción conviene usar una base de datos externa (por ejemplo **PostgreSQL** en Render o **Supabase**) y cambiar `app.py` para usarla. Mientras tanto, SQLite sirve para probar que todo funcione.
