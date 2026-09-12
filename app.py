import os
import io
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
import main as jarvis_main
import brain
import reminders

frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")

app = Flask(__name__, static_folder=frontend_dist, static_url_path="")

def on_reminder_due(reminder):
    print(f"\n[REMINDER] {reminder['task']}")

reminders.start_background_checker(on_reminder_due)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    return response



@app.route("/")
def home():
    if os.path.exists(os.path.join(frontend_dist, "index.html")):
        return send_from_directory(frontend_dist, "index.html")
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_message = data.get("message", "")
    file_attachment = data.get("file", None)

    file_data = None
    if file_attachment and isinstance(file_attachment, dict):
        try:
            import base64
            b64_str = file_attachment.get("data", "")
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            raw_bytes = base64.b64decode(b64_str)
            file_data = {
                "bytes": raw_bytes,
                "mime_type": file_attachment.get("mime_type", "image/png"),
                "filename": file_attachment.get("filename", "attachment")
            }
        except Exception as e:
            print(f"Error decoding base64 file attachment: {e}")

    if not user_message and not file_data:
        return jsonify({"reply": "I didn't receive anything."})

    command = user_message.lower().strip() if user_message else "please describe this attached file/image"
    reply = jarvis_main.respond(command, file_data=file_data)

    if reply is None:
        reply = "Goodbye! (Note: closing this chat won't stop the server.)"

    return jsonify({"reply": reply})



@app.route("/api/status", methods=["GET"])
def get_status():
    try:
        online = brain.is_online()
        facts = brain.get_facts()
        active_reminders = [r for r in reminders.load_reminders() if not r.get("done")]
        tutor_mode, tutor_topic = brain.get_tutor_mode() if hasattr(brain, "get_tutor_mode") else (False, "")
        return jsonify({
            "status": "online" if online else "offline",
            "online": online,
            "facts_count": len(facts),
            "reminders_count": len(active_reminders),
            "voice_supported": True,
            "tutor_mode": tutor_mode,
            "tutor_topic": tutor_topic
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/reminders", methods=["GET", "POST"])
def api_reminders():
    if request.method == "POST":
        data = request.get_json() or {}
        command = data.get("command", "")
        if command:
            res = reminders.add_reminder(command)
            return jsonify({"result": res, "reminders": reminders.load_reminders()})
        return jsonify({"error": "No command provided"}), 400
    
    return jsonify({"reminders": reminders.load_reminders()})


@app.route("/api/notes", methods=["GET", "POST"])
def api_notes():
    if request.method == "POST":
        data = request.get_json() or {}
        note = data.get("note", "")
        if note:
            res = jarvis_main.save_note(note)
            return jsonify({"result": res})
        return jsonify({"error": "No note provided"}), 400

    notes_text = jarvis_main.read_notes("")
    return jsonify({"notes": notes_text})


@app.route("/api/clear-memory", methods=["POST"])
def clear_memory():
    brain.reset_memory()
    notes_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.txt")
    if os.path.exists(notes_file):
        try:
            with open(notes_file, "w", encoding="utf-8") as f:
                f.write("")
        except Exception as e:
            print(f"Error clearing notes file: {e}")
    return jsonify({"result": "Memory wiped clean."})


@app.route("/api/tts", methods=["GET", "POST"])
def api_tts():
    text = request.args.get("text") or (request.get_json() or {}).get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    clean_text = text.replace("[Offline Mode]", "").strip()
    is_tamil = any('\u0B80' <= ch <= '\u0BFF' for ch in clean_text)
    
    # Use Microsoft Neural Male Voices: ta-IN-ValluvarNeural (Tamil Male) & en-US-ChristopherNeural (English Male)
    voice = "ta-IN-ValluvarNeural" if is_tamil else "en-US-ChristopherNeural"

    try:
        import asyncio
        import edge_tts

        fp = io.BytesIO()

        async def _stream():
            communicate = edge_tts.Communicate(clean_text, voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    fp.write(chunk["data"])

        asyncio.run(_stream())
        fp.seek(0)
        return send_file(fp, mimetype="audio/mpeg")
    except Exception as e:
        print(f"Edge-TTS male voice error: {e}, using gTTS fallback")
        try:
            from gtts import gTTS
            lang = 'ta' if is_tamil else 'en'
            tts = gTTS(text=clean_text, lang=lang)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            return send_file(fp, mimetype="audio/mpeg")
        except Exception as err:
            return jsonify({"error": str(err)}), 500



# Catch-all route to serve Vite built assets or React routing
@app.route("/<path:path>")
def serve_static(path):
    if os.path.exists(os.path.join(frontend_dist, path)):
        return send_from_directory(frontend_dist, path)
    if os.path.exists(os.path.join(frontend_dist, "index.html")):
        return send_from_directory(frontend_dist, "index.html")
    return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    print("\n==================================================")
    print("🚀 ZEN AI ASSISTANT IS LIVE!")
    print("👉 Open your browser at: http://localhost:5000")
    print("==================================================\n")
    import webbrowser
    webbrowser.open("http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)