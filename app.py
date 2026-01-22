from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import os
import time

# ====================
# Flask + SocketIO Setup
# ====================
app = Flask(__name__)
app.config["SECRET_KEY"] = "queue-system-secret"

# ใช้ eventlet เพื่อความเสถียรสูงสุดบน Render
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# ====================
# Global State
# ====================
last_queue = 0
current_queue = 0

# ====================
# Helper Functions
# ====================
def format_queue(n):
    return f"Q{n:03d}"

# ====================
# Routes
# ====================
@app.route("/")
@app.route("/counter")
def counter():
    return render_template("counter.html")

@app.route("/display")
def display():
    return render_template("display.html")

# ====================
# SocketIO Events
# ====================

@socketio.on("set_queue")
def set_queue(data):
    global current_queue, last_queue
    try:
        q = data.get("queue", "").upper().strip()
        # รับสถานะสวิตช์จากหน้า Counter
        voice_on_counter = data.get("voice_on_counter", False) 
        
        if not q.startswith("Q"): return
        number = int(q[1:])
        if number < 1 or number > 999: return # ปรับให้รันถึง 999 ตามที่มึงคุยไว้

        current_queue = number
        if current_queue > last_queue:
            last_queue = current_queue

        q_text = format_queue(current_queue)

        # 1. ส่งอัปเดตตัวเลขให้ทุกจอ
        emit("queue_updated", {
            "last": format_queue(last_queue),
            "current": q_text
        }, broadcast=True)

        # 2. 🎯 Logic ทางแยกเสียงตามสั่ง
        if voice_on_counter:
            # ถ้าเปิดสวิตช์: สั่งให้เฉพาะหน้า Counter พูด (ส่งไป Event เฉพาะ)
            emit("call_queue_locally", {"queue": q_text})
        else:
            # ถ้าปิดสวิตช์: สั่งให้หน้า Display พูด (ลูกค้าได้ยิน)
            emit("call_queue_display", {"queue": q_text}, broadcast=True)

    except:
        pass

@socketio.on("call_again")
def call_again(data=None):
    global current_queue
    # รับสถานะสวิตช์ (เผื่อกดปุ่มเรียกซ้ำ)
    voice_on_counter = data.get("voice_on_counter", False) if data else False
    
    if current_queue > 0:
        q_text = format_queue(current_queue)
        
        if voice_on_counter:
            emit("call_queue_locally", {"queue": q_text})
        else:
            emit("call_queue_display", {"queue": q_text}, broadcast=True)

@socketio.on("skip_order")
def skip_order():
    # ข้ามออเดอร์ให้ดังที่หน้า Display เสมอตามที่มึงเคยบอก
    emit("speak_only", {
        "msg": "ขออนุญาตข้ามออเดอร์นะคะ"
    }, broadcast=True)

@socketio.on("reset")
def reset():
    global last_queue, current_queue
    last_queue = 0
    current_queue = 0
    emit("queue_updated", {"last": "--", "current": "--"}, broadcast=True)
    emit("reset_done", broadcast=True)

# ====================
# Main execution
# ====================
if __name__ == "__main__":
    if not os.path.exists("static"):
        os.makedirs("static")
    socketio.run(app)
