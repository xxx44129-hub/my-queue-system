from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import os

# ====================
# Flask + SocketIO Setup
# ====================
app = Flask(__name__)
app.config["SECRET_KEY"] = "queue-system-secret"

# ใช้ eventlet เพื่อความเสถียรบน Render และรองรับการทำงานแบบ Real-time
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
    """แปลงตัวเลขเป็นรูปแบบ Q001"""
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
    """จัดการการเรียกคิว ทั้ง Next, Set และ Again"""
    global current_queue, last_queue
    try:
        q = data.get("queue", "").upper().strip()
        # รับสถานะสวิตช์จากหน้า Counter ว่าจะให้เสียงดังที่ไหน
        voice_on_counter = data.get("voice_on_counter", False) 
        
        if not q.startswith("Q"): return
        number = int(q[1:])
        if number < 0: return

        current_queue = number
        # อัปเดตคิวสูงสุดในระบบ
        if current_queue > last_queue:
            last_queue = current_queue

        q_text = format_queue(current_queue)

        # 1. ส่งสัญญาณอัปเดตตัวเลขให้ทุกหน้าจอ (Counter & Display)
        emit("queue_updated", {
            "last": format_queue(last_queue),
            "current": q_text
        }, broadcast=True)

        # 2. 🎯 จัดการเส้นทางเสียง (Voice Routing)
        if voice_on_counter:
            # ถ้าเปิดสวิตช์ที่ Counter: ส่งเสียงไปเฉพาะเครื่องที่กด
            emit("call_queue_locally", {"queue": q_text})
        else:
            # ถ้าปิดสวิตช์ที่ Counter: ส่งเสียงไปที่หน้า Display (และทุกจอที่เปิดทิ้งไว้)
            emit("call_queue_display", {"queue": q_text}, broadcast=True)
    except Exception as e:
        print(f"Error: {e}")

@socketio.on("skip_order")
def skip_order(data):
    """จัดการการข้ามออเดอร์ ให้เสียงวิ่งตามสวิตช์เหมือนการเรียกคิว"""
    # รับสถานะสวิตช์จากหน้า Counter
    voice_on_counter = data.get("voice_on_counter", False) if data else False
    msg_text = "ขออนุญาตข้ามออเดอร์นะคะ"

    if voice_on_counter:
        # 🎯 ถ้าเปิดสวิตช์: ให้ดังแค่ที่หน้า Counter
        emit("speak_locally", {"msg": msg_text})
    else:
        # 🎯 ถ้าปิดสวิตช์: ให้ไปดังที่หน้า Display
        emit("speak_only", {"msg": msg_text}, broadcast=True)

@socketio.on("reset")
def reset():
    """ล้างคิวทั้งหมดเริ่มใหม่"""
    global last_queue, current_queue
    last_queue = 0
    current_queue = 0
    emit("queue_updated", {"last": "--", "current": "--"}, broadcast=True)
    emit("reset_done", broadcast=True)

# ====================
# Main execution
# ====================
if __name__ == "__main__":
    # ตรวจสอบ Folder Static เผื่อไว้
    if not os.path.exists("static"):
        os.makedirs("static")
    
    # รันเซิร์ฟเวอร์
    socketio.run(app, debug=True)
