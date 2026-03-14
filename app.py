from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from flask import Flask, abort, jsonify, request, send_file


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "taller.db"

ALLOWED_EXTENSIONS = {
    ".html",
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".svg",
    ".ico",
    ".txt",
    ".md",
}

app = Flask(__name__)


@app.after_request
def _cors(response):
    """Permite peticiones desde Firebase Hosting (y otros orígenes) al backend en Render/Railway."""
    origin = request.environ.get("HTTP_ORIGIN")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/api/citas", methods=["OPTIONS"])
def _cors_preflight_citas():
    return "", 204


@app.route("/api/citas/<int:appointment_id>/finalizar", methods=["OPTIONS"])
def _cors_preflight_finalizar(appointment_id):
    return "", 204


def _safe_path(filename: str) -> Path:
    requested = (BASE_DIR / filename).resolve()
    if requested == BASE_DIR or BASE_DIR not in requested.parents:
        abort(404)
    if not requested.is_file():
        abort(404)
    if requested.suffix.lower() not in ALLOWED_EXTENSIONS:
        abort(404)
    return requested


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _get_connection() as conn:
        conn.execute(
            """
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
            """
        )
        conn.commit()


def _send_email(to_email: str, subject: str, body: str) -> None:
    """
    Envío simple de correo usando SMTP.
    Configura estas variables de entorno en el servidor:
    - EMAIL_HOST
    - EMAIL_PORT
    - EMAIL_USER
    - EMAIL_PASSWORD
    - EMAIL_FROM (opcional, por defecto EMAIL_USER)
    """
    host = os.environ.get("EMAIL_HOST")
    port = int(os.environ.get("EMAIL_PORT", "587"))
    user = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASSWORD")
    sender = os.environ.get("EMAIL_FROM") or user

    if not (host and user and password and sender):
        # Para entorno de desarrollo / sin configuración real solo se imprime
        print("=== EMAIL (SIMULADO) ===")
        print("Para:", to_email)
        print("Asunto:", subject)
        print("Cuerpo:\n", body)
        print("========================")
        return

    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


@app.get("/")
def home():
    return send_file(BASE_DIR / "index.html")


@app.get("/<path:filename>")
def files(filename: str):
    return send_file(_safe_path(filename))


@app.post("/api/citas")
def crear_cita():
    data: Dict[str, Any] = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    name = data.get("nombre") or data.get("name")
    email = data.get("email")
    phone = data.get("telefono") or data.get("phone")
    service_type = data.get("servicio") or data.get("service_type")
    vehicle = data.get("vehiculo") or data.get("vehicle")
    plate = data.get("placa") or data.get("plate")
    requested_date = data.get("fecha") or data.get("requested_date")
    notes = data.get("notas") or data.get("notes")

    if not all([name, email, phone, service_type, requested_date]):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Faltan campos obligatorios (nombre, email, teléfono, servicio, fecha).",
                }
            ),
            400,
        )

    now = datetime.utcnow().isoformat()

    with _get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO appointments (
                name, email, phone, service_type, vehicle, plate,
                requested_date, notes, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?, ?)
            """,
            (
                name,
                email,
                phone,
                service_type,
                vehicle,
                plate,
                requested_date,
                notes,
                now,
                now,
            ),
        )
        appointment_id = cur.lastrowid
        conn.commit()

    body = (
        f"Hola {name},\n\n"
        "Hemos recibido su solicitud de cita en Taller Loro.\n\n"
        f"Servicio: {service_type}\n"
        f"Fecha solicitada: {requested_date}\n"
        f"Teléfono de contacto: {phone}\n"
        f"Vehículo: {vehicle or '-'} | Placa: {plate or '-'}\n\n"
        "Nos comunicaremos con usted para confirmar la hora exacta.\n\n"
        "Gracias por confiar en Taller Loro."
    )
    _send_email(email, "Confirmación de solicitud de cita - Taller Loro", body)

    return jsonify({"ok": True, "id": appointment_id})


@app.post("/api/citas/<int:appointment_id>/finalizar")
def finalizar_cita(appointment_id: int):
    now = datetime.utcnow().isoformat()

    with _get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Cita no encontrada"}), 404

        conn.execute(
            "UPDATE appointments SET status = ?, updated_at = ? WHERE id = ?",
            ("finalizado", now, appointment_id),
        )
        conn.commit()

    email = row["email"]
    name = row["name"]
    service_type = row["service_type"]

    body = (
        f"Hola {name},\n\n"
        "Su servicio en Taller Loro ha sido finalizado.\n\n"
        f"Servicio: {service_type}\n\n"
        "Puede pasar a retirar su vehículo / equipo en nuestro taller.\n\n"
        "Muchas gracias por su preferencia.\n"
        "Taller Loro."
    )
    _send_email(email, "Servicio finalizado - Taller Loro", body)

    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
