from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from gtts import gTTS
import os
import time  # เพิ่มมาเพื่อใช้ทำชื่อไฟล์ไม่ให้ซ้ำ

# ====================
# Flask + SocketIO Config
# ====================
app = Flask(__name__)
app.config["SECRET_KEY"] = "queue-system-secret"

# ปรับ async_mode เป็น eventlet ให้ตรงกับ Start Command บน Render
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# ====================
# Global state
# ====================
last_queue = 0
current_queue = 0

STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)

# ====================
# Helper functions
# ====================
def format_queue(n):
    return f"Q{n:03d}"

def queue_to_thai(queue):
    mapping = {
        "0": "ศูนย์", "1": "หนึ่ง", "2": "สอง", "3": "สาม", "4": "สี่",
        "5": "ห้า", "6": "หก", "7": "เจ็ด", "8": "แปด", "9": "เก้า",
        "Q": "คิว"
    }
    return " ".join(mapping.get(c, c) for c in queue)

def generate_tts(text, filename_prefix):
    # แก้ไข: เพิ่ม timestamp เข้าไปในชื่อไฟล์เพื่อให้ Render สร้างไฟล์ใหม่ตลอด
    # ป้องกันปัญหาไฟล์เก่าค้างหรือโดนลบแล้วหาไม่เจอ (ตัวการที่ทำให้ไม่มีเสียง)
    ts = int(time.time())
    filename = f"{filename_prefix}_{ts}.mp3"
    path = os.path.join(STATIC_DIR, filename)

    # บังคับสร้างใหม่เสมอเพื่อความชัวร์ว่าเสียงมาแน่
    gTTS(text=text, lang="th", slow=False).save(path)
    os.chmod(path, 0o644)

    return f"/static/{filename}"

# ====================
# Routes (แก้ให้เข้าได้ทุกทาง)
# ====================
@app.route("/")
@app.route("/counter")
def counter_page():
    # เข้าได้ทั้งหน้าหลัก และ /counter
    return render_template("counter.html")

@app.route("/display")
def display_page():
    # หน้าจอแสดงผลสำหรับลูกค้า/ทีวี
    return render_template("display.html")

# ====================
# SocketIO events
# ====================

@socketio.on("set_queue")
def set_queue(data):
    global current_queue, last_queue
    try:
        q = data.get("queue", "").upper().strip()
        if not q.startswith("Q"): return
        number = int(q[1:])
        if number < 1 or number > 500: return

        current_queue = number
        if current_queue > last_queue:
            last_queue = current_queue

        emit("queue_updated", {
            "last": format_queue(last_queue),
            "current": format_queue(current_queue)
        }, broadcast=True)
    except:
        pass

@socketio.on("new_queue")
def new_queue():
    global last_queue
    if last_queue < 500:
        last_queue += 1
    emit("queue_updated", {
        "last": format_queue(last_queue),
        "current": format_queue(current_queue) if current_queue else "--"
    }, broadcast=True)

@socketio.on("call_next")
def call_next():
    global current_queue
    if current_queue < last_queue:
        current_queue += 1
        q_text = format_queue(current_queue)
        # แก้ไขข้อความให้นุ่มนวลขึ้นตามที่มึงต้องการ
        audio = generate_tts(f"เชิญหมายเลข {queue_to_thai(q_text)} ค่ะ", q_text)
        emit("call_queue", { "queue": q_text, "audio": audio }, broadcast=True)

@socketio.on("call_again")
def call_again():
    global current_queue
    if current_queue > 0:
        q_text = format_queue(current_queue)
        audio = generate_tts(f"เชิญหมายเลข {queue_to_thai(q_text)} ค่ะ", q_text)
        emit("call_queue", { "queue": q_text, "audio": audio }, broadcast=True)

@socketio.on("skip_order")
def skip_order():
    audio = generate_tts("ขออนุญาตข้าม ออเดอร์ นะคะ", "skip_msg")
    emit("speak_only", {"audio": audio}, broadcast=True)

@socketio.on("reset")
def reset():
    global last_queue, current_queue
    last_queue = 0
    current_queue = 0
    emit("queue_updated", {"last": "--", "current": "--"}, broadcast=True)

# ====================
# Main
# ====================
if __name__ == "__main__":
    socketio.run(app)
