from __future__ import annotations

import os
import sqlite3
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "taller.db"
DEFAULT_NOTIFY_EMAIL = "xviia1212@gmail.com"

app = Flask(__name__)


def _get_connection() -> sqlite3.Connection:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn
    
@app.before_request
def setup():
    init_db()

def init_db() -> None:
    conn = _get_connection()
    try:
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
    finally:
        conn.close()


def _send_email(to_email: str, subject: str, body: str) -> None:
    host = os.environ.get("EMAIL_HOST")
    port = int(os.environ.get("EMAIL_PORT", "587"))
    user = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASSWORD")
    sender = os.environ.get("EMAIL_FROM") or user

    if not (host and user and password and sender and to_email):
        print("=== EMAIL (simulado) ===")
        print("Para:", to_email, "| Asunto:", subject)
        print(body)
        print("=======================")
        return

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


def _parse_cita_data() -> Dict[str, Any]:
    data = request.form.to_dict()
    return {
        "name": data.get("nombre"),
        "email": data.get("email"),
        "phone": data.get("telefono"),
        "service_type": data.get("servicio"),
        "vehicle": data.get("vehiculo"),
        "plate": data.get("placa"),
        "requested_date": data.get("fecha"),
        "notes": data.get("notas"),
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

    body_cliente = (
        f"Hola {name},\n\n"
        "Hemos recibido su solicitud de cita en Taller Loro.\n\n"
        f"Servicio: {service_type}\n"
        f"Fecha solicitada: {requested_date}\n"
        f"Teléfono de contacto: {phone}\n"
        f"Vehículo: {vehicle or '-'} | Placa: {plate or '-'}\n\n"
        "Nos comunicaremos con usted para confirmar la hora exacta.\n\n"
        "Gracias por confiar en Taller Loro."
    )
    _send_email(email, "Confirmación de solicitud de cita - Taller Loro", body_cliente)

    notify = os.environ.get("NOTIFY_EMAIL") or DEFAULT_NOTIFY_EMAIL
    body_taller = (
        f"Nueva solicitud de cita (#{appointment_id})\n\n"
        f"Nombre: {name}\nEmail: {email}\nTeléfono: {phone}\n"
        f"Servicio: {service_type}\nFecha solicitada: {requested_date}\n"
        f"Vehículo: {vehicle or '-'}\nPlaca: {plate or '-'}\n"
        f"Comentario: {notes or '-'}\n"
    )
    _send_email(notify, "Nueva cita - Taller Loro", body_taller)

    return jsonify({"ok": True, "id": appointment_id})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

