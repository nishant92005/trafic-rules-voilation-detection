# AI Traffic Violation Detection System

Flask-based computer vision demo for:

- Helmet violation detection
- Triple riding detection
- Processed video output with overlays
- SMTP alert integration with optional GROQ-generated email text

## Project Structure

- `app.py`
- `detection.py`
- `email_alert.py`
- `templates/index.html`
- `static/css/styles.css`
- `static/js/app.js`
- `uploads/`
- `outputs/`

## Frontend Stack

- HTML
- Tailwind CSS via CDN
- Vanilla JavaScript
- Three.js via CDN for the animated hero object

No Tailwind build step is required for this demo.

## Run Locally

1. Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

2. Start the Flask app:

```powershell
python app.py
```

3. Open:

```text
http://127.0.0.1:5000
```

## Optional Environment Variables

Set these if you want email alerts and GROQ-generated email bodies:

```powershell
$env:SMTP_SERVER="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USER="your_email@example.com"
$env:SMTP_PASSWORD="your_app_password"
$env:SENDER_EMAIL="your_email@example.com"
$env:RECEIVER_EMAIL="receiver@example.com"

$env:GROQ_API_KEY="your_groq_api_key"
$env:GROQ_MODEL="llama3-8b-8192"
```

Speed/quality tuning:

```powershell
$env:DETECTION_FRAME_SKIP="5"
$env:DETECTION_INFERENCE_WIDTH="480"
$env:DETECTION_CONFIDENCE="0.35"
$env:ENABLE_EMAIL_ALERTS="1"
```

- Increase `DETECTION_FRAME_SKIP` for faster analysis. Use `3` for better accuracy, `8` or `10` for faster demos.
- Lower `DETECTION_INFERENCE_WIDTH` for faster analysis. Use `416` for speed, `640` for better detection quality.
- Keep `ENABLE_EMAIL_ALERTS=1` to send SMTP alerts when violations are detected. Set it to `0` only for faster demos without email.

## Notes

- The first detection run may download `yolov8n.pt` if it is not already cached.
- Helmet detection is an approximation built on top of person and motorcycle detection plus head-region analysis.
- Processed videos are written to `outputs/`.
- Uploaded source videos are written to `uploads/`.

## Deploy on Render

This repo is configured for Render with:

- `requirements.txt`
- `render.yaml`
- a health endpoint at `/healthz`

### Recommended deploy steps

1. Push this project to GitHub.
2. Sign in to Render.
3. Create a new Blueprint or Web Service from the repo.
4. Render should detect:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Add these environment variables in Render:

```text
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama3-8b-8192
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_email@example.com
SENDER_PASSWORD=your_gmail_app_password
RECEIVER_EMAIL=receiver@example.com
FLASK_DEBUG=0
PYTHON_VERSION=3.11.11
```

### Important deployment notes

- Render can use the `PYTHON_VERSION=3.11.11` value from `render.yaml`, which is the recommended deployment target for this project.
- `uploads/` and `outputs/` are ephemeral on Render unless you attach a persistent disk.
- If you want processed videos and snapshots to survive restarts and redeploys, add a persistent disk in Render.
- This project uses YOLO and OpenCV, so a paid Render instance is more realistic than a tiny free instance for video processing workloads.

## Deploy on Vercel

This repo now includes `vercel.json` and a Vercel-compatible `.python-version` (`3.12`) so builds can start correctly on Vercel.

Important limitations still apply:

- Vercel is best for lightweight Flask apps, not long-running video inference workloads.
- Large video uploads, generated output files, and YOLO/OpenCV processing may still hit Vercel platform limits.
- For reliable full-stack deployment of this project, Render remains the recommended backend host.
