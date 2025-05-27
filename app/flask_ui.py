import os
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = "secure-autotheft-key"  # Required for flash messages

# FastAPI backend base URL
FASTAPI_URL = "http://localhost:8000"

@app.route('/app', methods=['GET', 'POST'])
def index():
    video_uploaded = False
    stream_connected = False
    error_msg = None

    if request.method == 'POST':
        # Handle video file upload
        video = request.files.get('video')
        stream_url = request.form.get('stream_url')

        if video and video.filename != "":
            files = {'video': (video.filename, video.stream, video.mimetype)}
            try:
                res = requests.post(f"{FASTAPI_URL}/upload_video", files=files)
                if res.ok:
                    flash("Video uploaded successfully", "success")
                    video_uploaded = True
                else:
                    flash("Failed to upload video", "danger")
            except Exception as e:
                flash(f"Upload error: {e}", "danger")

        # Handle stream URL input
        elif stream_url:
            try:
                res = requests.post(f"{FASTAPI_URL}/set_stream_url", params={"url": stream_url})
                if res.ok:
                    flash("Stream connected successfully", "success")
                    stream_connected = True
                else:
                    flash("Invalid stream URL", "danger")
            except Exception as e:
                flash(f"Stream error: {e}", "danger")

        else:
            flash("No input provided. Upload a file or enter a stream URL.", "warning")

    return render_template(
        "index.html",
        video_uploaded=video_uploaded,
        stream_connected=stream_connected
    )


@app.route('/app/video_feed')
def video_feed():
    return redirect(f"{FASTAPI_URL}/video_feed", code=307)


@app.route('/app/stolen_plates')
def stolen_plates():
    try:
        res = requests.get(f"{FASTAPI_URL}/stolen_plates")
        return jsonify(res.json())
    except Exception:
        return jsonify({"stolen_plates": []})


@app.route('/app/is_theft')
def is_theft():
    try:
        res = requests.get(f"{FASTAPI_URL}/is_theft")
        return jsonify(res.json())
    except Exception:
        return jsonify({"is_theft": False})


@app.route('/app/plates/add', methods=['POST'])
def add_plate():
    plate = request.form.get("plate")
    if not plate:
        return jsonify({"error": "No plate provided"}), 400

    try:
        res = requests.post(f"{FASTAPI_URL}/plates/add", json={"plate": plate})
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/app/plates/delete', methods=['POSTS'])
def delete_plate():
    plate = request.args.get("plate")
    if not plate:
        return jsonify({"error": "No plate provided"}), 400

    try:
        res = requests.delete(f"{FASTAPI_URL}/plates/delete", json={"plate": plate})
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)
