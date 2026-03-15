"""
Taller Loro - Backend.
Sirve la web estática y la API de citas (crear, finalizar) con envío de correos.
"""
from __future__ import annotations

import os
import sys
import sqlite3
import traceback
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict

from flask import Flask, abort, jsonify, make_response, request, send_file


# -----------------------------------------------------------------------------
# Configuración
# -----------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"  # Única carpeta de web estática (Firebase + Flask)
# En Render el disco del proyecto es de solo lectura; usar /tmp (escribible, efímero)
DATABASE = Path(
    os.environ.get("DATABASE_PATH")
    or ("/tmp/taller.db" if os.environ.get("RENDER") else str(BASE_DIR / "taller.db"))
)
DEFAULT_NOTIFY_EMAIL = "xviia1212@gmail.com"

ALLOWED_EXTENSIONS = {
    ".html", ".css", ".js",
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico",
    ".txt", ".md",
}

app = Flask(__name__)


# -----------------------------------------------------------------------------
# CORS (para peticiones desde Firebase Hosting)
# -----------------------------------------------------------------------------

def _cors_headers_response():
    """Cabeceras CORS para respuestas de la API (evitar fallo de red por CORS)."""
    origin = request.environ.get("HTTP_ORIGIN", "*")
    r = make_response()
    r.headers["Access-Control-Allow-Origin"] = origin
    r.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
    r.headers["Access-Control-Max-Age"] = "86400"
    return r


@app.after_request
def _cors_headers(response):
    origin = request.environ.get("HTTP_ORIGIN")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
    return response


@app.route("/api/citas", methods=["OPTIONS"])
def _cors_preflight_citas():
    r = _cors_headers_response()
    r.status_code = 204
    return r


@app.route("/api/citas/<int:appointment_id>/finalizar", methods=["OPTIONS"])
def _cors_preflight_finalizar(appointment_id: int):
    r = _cors_headers_response()
    r.status_code = 204
    return r


@app.get("/api/health")
def health():
    """Comprueba que el backend esté en marcha (útil con Render)."""
    return jsonify({"ok": True})


# -----------------------------------------------------------------------------
# Base de datos
# -----------------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATABASE), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                service_type TEXT NOT NULL,
                vehicle TEXT,
                plate TEXT,
                requested_date TEXT NOT NULL,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'pendiente',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# Archivos estáticos (rutas seguras)
# -----------------------------------------------------------------------------

def _safe_path(filename: str) -> Path:
    requested = (PUBLIC_DIR / filename).resolve()
    try:
        requested.relative_to(PUBLIC_DIR.resolve())
    except ValueError:
        abort(404)
    if not requested.is_file() or requested.suffix.lower() not in ALLOWED_EXTENSIONS:
        abort(404)
    return requested


# -----------------------------------------------------------------------------
# Correo
# -----------------------------------------------------------------------------

def _send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Envía correo por SMTP. Variables de entorno: EMAIL_HOST, EMAIL_PORT,
    EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM (opcional).
    Si no están configuradas, imprime el mensaje en consola (desarrollo).
    Devuelve True si se envió o se simuló; False si hubo error o el destinatario está vacío.
    """
    if not (to_email and str(to_email).strip()):
        return False

    host = os.environ.get("EMAIL_HOST")
    port = int(os.environ.get("EMAIL_PORT", "587"))
    user = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASSWORD")
    sender = (os.environ.get("EMAIL_FROM") or user or "").strip()

    if not (host and user and password and sender):
        print("=== EMAIL (simulado) ===")
        print("Para:", to_email, "| Asunto:", subject)
        print(body)
        print("=======================")
        return True

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email.strip()

        with smtplib.SMTP(host, int(port)) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print("[EMAIL] Error al enviar a", to_email, ":", e)
        return False


def _body_confirmacion_cliente(name: str, service_type: str, requested_date: str,
                               phone: str, vehicle: str, plate: str) -> str:
    return (
        f"Hola {name},\n\n"
        "Hemos recibido su solicitud de cita en Taller Loro.\n\n"
        f"Servicio: {service_type}\n"
        f"Fecha solicitada: {requested_date}\n"
        f"Teléfono de contacto: {phone}\n"
        f"Vehículo: {vehicle or '-'} | Placa: {plate or '-'}\n\n"
        "Nos comunicaremos con usted para confirmar la hora exacta.\n\n"
        "Gracias por confiar en Taller Loro."
    )


def _body_notificacion_taller(appointment_id: int, name: str, email: str,
                              phone: str, service_type: str, requested_date: str,
                              vehicle: str, plate: str, notes: str) -> str:
    return (
        f"Nueva solicitud de cita (#{appointment_id})\n\n"
        f"Nombre: {name}\nEmail: {email}\nTeléfono: {phone}\n"
        f"Servicio: {service_type}\nFecha solicitada: {requested_date}\n"
        f"Vehículo: {vehicle or '-'}\nPlaca: {plate or '-'}\n"
        f"Comentario: {notes or '-'}\n"
    )


def _body_trabajo_finalizado(name: str, service_type: str) -> str:
    return (
        f"Hola {name},\n\n"
        "Su servicio en Taller Loro ha sido finalizado.\n\n"
        f"Servicio: {service_type}\n\n"
        "Puede pasar a retirar su vehículo / equipo en nuestro taller.\n\n"
        "Muchas gracias por su preferencia.\nTaller Loro."
    )


# -----------------------------------------------------------------------------
# Rutas: sitio estático
# -----------------------------------------------------------------------------

@app.get("/")
def home():
    return send_file(PUBLIC_DIR / "index.html")


@app.get("/<path:filename>")
def static_file(filename: str):
    return send_file(_safe_path(filename))


# -----------------------------------------------------------------------------
# Rutas: API citas
# -----------------------------------------------------------------------------

def _parse_cita_data() -> Dict[str, Any]:
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()
    return {
        "name": data.get("nombre") or data.get("name"),
        "email": data.get("email"),
        "phone": data.get("telefono") or data.get("phone"),
        "service_type": data.get("servicio") or data.get("service_type"),
        "vehicle": data.get("vehiculo") or data.get("vehicle"),
        "plate": data.get("placa") or data.get("plate"),
        "requested_date": data.get("fecha") or data.get("requested_date"),
        "notes": data.get("notas") or data.get("notes"),
    }


@app.post("/api/citas")
def crear_cita():
    data = _parse_cita_data()
    name = data["name"]
    email = data["email"]
    phone = data["phone"]
    service_type = data["service_type"]
    requested_date = data["requested_date"]

    if not all([name, email, phone, service_type, requested_date]):
        return jsonify({
            "ok": False,
            "error": "Faltan campos obligatorios (nombre, email, teléfono, servicio, fecha).",
        }), 400

    now = datetime.utcnow().isoformat()
    vehicle = data["vehicle"]
    plate = data["plate"]
    notes = data["notes"]

    try:
        conn = _get_connection()
        try:
            cur = conn.execute(
                """
                INSERT INTO appointments (
                    name, email, phone, service_type, vehicle, plate,
                    requested_date, notes, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?, ?)
                """,
                (name, email, phone, service_type, vehicle, plate,
                 requested_date, notes, now, now),
            )
            appointment_id = cur.lastrowid
            conn.commit()
        finally:
            conn.close()

        # Confirmación al cliente (si falla el correo, la cita ya está guardada)
        _send_email(
            (email or "").strip(),
            "Confirmación de solicitud de cita - Taller Loro",
            _body_confirmacion_cliente(name, service_type, requested_date, phone, vehicle, plate),
        )

        # Notificación al taller
        notify = (os.environ.get("NOTIFY_EMAIL") or "").strip() or DEFAULT_NOTIFY_EMAIL
        _send_email(
            notify,
            "Nueva cita - Taller Loro",
            _body_notificacion_taller(
                appointment_id, name, email, phone, service_type,
                requested_date, vehicle, plate, notes,
            ),
        )

        return jsonify({"ok": True, "id": appointment_id})
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            "ok": False,
            "error": "Error interno al guardar la cita. Intenta de nuevo o contáctanos por WhatsApp.",
        }), 500


@app.post("/api/citas/<int:appointment_id>/finalizar")
def finalizar_cita(appointment_id: int):
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Cita no encontrada"}), 404
        row = dict(zip(row.keys(), row))  # copia para usar tras cerrar la conexión
        conn.execute(
            "UPDATE appointments SET status = ?, updated_at = ? WHERE id = ?",
            ("finalizado", datetime.utcnow().isoformat(), appointment_id),
        )
        conn.commit()
    finally:
        conn.close()

    # Si falla el correo, el estado ya quedó actualizado
    _send_email(
        (row.get("email") or "").strip(),
        "Servicio finalizado - Taller Loro",
        _body_trabajo_finalizado(row["name"], row["service_type"]),
    )
    return jsonify({"ok": True})


# -----------------------------------------------------------------------------
# Arranque
# -----------------------------------------------------------------------------

# Crear tabla si no existe (también al importar en Render con waitress)
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
