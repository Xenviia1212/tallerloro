# Taller Loro - Flask + Render + Firebase Hosting

Este proyecto es un sitio web estático (HTML/CSS) con un backend en **Flask** desplegado en **Render** para guardar citas en SQLite y enviar correos de confirmación. El sitio estático se sirve desde **Firebase Hosting**.

## Estructura

- `public/` → sitio web (HTML, CSS, páginas de Mecánica y Alquiler), desplegado en Firebase Hosting.
- `app.py` → backend Flask con la ruta `POST /api/citas`, desplegado en Render.
- `requirements.txt` → dependencias de Python para Render.
- `firebase.json` → configuración mínima de Firebase Hosting apuntando a `public/`.

## Flujo de la cita

1. El cliente rellena el formulario en `public/index.html` (servido por Firebase Hosting).
2. El formulario envía un `POST` a `https://tallerloro.onrender.com/api/citas` (servicio en Render).
3. El backend Flask:
   - Valida los datos.
   - Guarda la cita en `taller.db` (SQLite).
   - Envía un correo a `xviia1212@gmail.com` (o `NOTIFY_EMAIL`) con los datos de la cita.
   - Envía un correo de confirmación al cliente.

## Despliegue backend en Render

1. Sube este proyecto a GitHub.
2. Crea un **Web Service** en Render desde el repo.
3. Configura:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `waitress-serve --listen=0.0.0.0:$PORT app:app`
4. En las variables de entorno de Render configura:
   - `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_FROM` (para SMTP).
   - Opcional: `NOTIFY_EMAIL` para cambiar el correo que recibe las citas.

## Despliegue frontend en Firebase Hosting

1. Instala las herramientas de Firebase si no las tienes: `npm install -g firebase-tools`.
2. Inicia sesión: `firebase login`.
3. Asegúrate de tener `firebase.json` en la raíz con:

   ```json
   {
     "hosting": {
       "public": "public",
       "ignore": [
         "firebase.json",
         "**/.*",
         "**/node_modules/**"
       ]
     }
   }
   ```

4. Ejecuta `firebase init hosting` solo si aún no has asociado este proyecto local con tu proyecto de Firebase.
5. Despliega el sitio estático: `firebase deploy --only hosting`.

## Formulario

En `public/index.html`, el formulario debe tener:

```html
<form class="booking-form"
      id="form-citas"
      action="https://tallerloro.onrender.com/api/citas"
      method="post">
```

con los campos `name` ya definidos (`nombre, email, telefono, servicio, vehiculo, placa, fecha, notas`).
