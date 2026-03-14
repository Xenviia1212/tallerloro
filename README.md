# Taller Loro (web) + Python (Flask)

Este proyecto es un sitio web estático (HTML/CSS) servido con una mini app de **Python + Flask**, para que puedas abrirlo desde el navegador como un sitio “real” (con URL local) y luego desplegarlo en un hosting.

## Requisitos

- Python 3.10+ (recomendado)

## Ejecutar en tu PC (Windows)

Abre PowerShell en la carpeta del proyecto y corre:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Luego abre en tu navegador:

- `http://localhost:5000`

## Publicar (Deploy) con Python

### Opción recomendada: Render (simple)

1. Sube el proyecto a GitHub.
2. En Render crea un **Web Service** desde el repo.
3. Configura:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `waitress-serve --listen=0.0.0.0:$PORT app:app`

### Opción alternativa: Railway

Similar: usa el mismo build y start command.

## Notas

- Esta app sirve archivos desde la carpeta del proyecto (solo extensiones permitidas).
- Si agregas imágenes (por ejemplo `logo.png`), funcionarán automáticamente.
