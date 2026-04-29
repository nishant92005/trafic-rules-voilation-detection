import os
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from config import load_env


load_env()


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
SNAPSHOT_DIR = OUTPUT_DIR / "snapshots"

for directory in (UPLOAD_DIR, OUTPUT_DIR, SNAPSHOT_DIR):
    directory.mkdir(parents=True, exist_ok=True)


ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


@app.route("/upload", methods=["POST"])
def upload_video():
    file = request.files.get("video")
    if not file or file.filename == "":
        return jsonify({"success": False, "message": "No video selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Unsupported file format."}), 400

    extension = file.filename.rsplit(".", 1)[1].lower()
    safe_name = secure_filename(file.filename.rsplit(".", 1)[0])
    unique_name = f"{safe_name}-{uuid4().hex[:8]}.{extension}"
    save_path = UPLOAD_DIR / unique_name
    file.save(save_path)

    return jsonify(
        {
            "success": True,
            "filename": unique_name,
            "preview_url": f"/uploads/{unique_name}",
            "message": "Video uploaded. Ready for AI analysis.",
        }
    )


@app.route("/process", methods=["POST"])
def process_route():
    from detection import process_video

    payload = request.get_json(silent=True) or {}
    filename = payload.get("filename")

    if not filename:
        return jsonify({"success": False, "message": "Missing filename."}), 400

    input_path = UPLOAD_DIR / filename
    if not input_path.exists():
        return jsonify({"success": False, "message": "Uploaded video not found."}), 404

    output_name = f"processed-{Path(filename).stem}.mp4"
    output_path = OUTPUT_DIR / output_name

    try:
        result = process_video(str(input_path), str(output_path), str(SNAPSHOT_DIR))
    except Exception as exc:
        return jsonify(
            {
                "success": False,
                "message": (
                    "Detection could not start. This is often caused by a PyTorch/Ultralytics "
                    f"runtime issue in the current Python environment. Details: {exc}"
                ),
            }
        ), 500

    result["processed_video_url"] = f"/outputs/{output_name}"
    result["original_filename"] = filename

    return jsonify(result)


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/outputs/<path:filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=debug)
