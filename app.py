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
# Helper Functions (กูเก็บไว้ครบตามต้นฉบับมึง)
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
        if not q.startswith("Q"): return
        number = int(q[1:])
        if number < 1 or number > 500: return

        current_queue = number
        if current_queue > last_queue:
            last_queue = current_queue

        # ส่งสัญญาณอัปเดตเลขให้ทุกจอทันที
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
    # อัปเดตฝั่งคนรับคิวใหม่
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
        
        # 🎯 แก้เลขดีเลย์: ส่งสัญญาณที่มีทั้งเลขและเสียง (รหัสคิวเพียวๆ) ไปพร้อมกัน
        emit("call_queue", { 
            "queue": q_text, 
            "msg": q_text 
        }, broadcast=True)
        
        # อัปเดตตัวเลขหน้าเคาน์เตอร์ให้ตรงกัน
        emit("queue_updated", {
            "last": format_queue(last_queue),
            "current": q_text
        }, broadcast=True)

@socketio.on("call_again")
def call_again():
    if current_queue > 0:
        q_text = format_queue(current_queue)
        # เรียกซ้ำ อ่านแค่รหัสคิว
        emit("call_queue", { 
            "queue": q_text, 
            "msg": q_text 
        }, broadcast=True)

@socketio.on("skip_order")
def skip_order():
    # 🎯 แก้ไขประโยคตามที่มึงขอ: "ขออนุญาตข้ามคิวนะคะ"
    emit("speak_only", {
        "msg": "ขออนุญาตข้ามคิวนะคะ"
    }, broadcast=True)

@socketio.on("reset")
def reset():
    global last_queue, current_queue
    last_queue = 0
    current_queue = 0
    emit("queue_updated", {"last": "--", "current": "--"}, broadcast=True)

# ====================
# Main execution
# ====================
if __name__ == "__main__":
    # เช็คโฟลเดอร์ static ตามต้นฉบับเดิม
    if not os.path.exists("static"):
        os.makedirs("static")
    socketio.run(app)
