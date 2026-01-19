<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<title>Queue Display</title>

<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>

<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black">
<meta name="apple-mobile-web-app-title" content="Queue Display">
<link rel="apple-touch-icon" href="/static/icon-512.png">

<style>
body {
    margin: 0;
    font-family: "Segoe UI", Arial, sans-serif;
    background: linear-gradient(135deg, #0f2027, #2c5364);
    color: white;
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
}
.container { text-align: center; }
.queue {
    font-size: 240px;
    font-weight: bold;
    color: #ffd700;
    text-shadow: 0 10px 20px rgba(0,0,0,0.5);
    animation: pop 0.4s ease-out;
}
.subtitle { font-size: 42px; margin-top: 20px; }

@keyframes pop {
    from { transform: scale(0.5); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
}

/* overlay ปลดล็อกเสียง */
#unlock {
    position: fixed;
    inset: 0;
    background: black;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 48px;
    z-index: 9999;
    text-align: center;
    cursor: pointer;
}
</style>
</head>

<body>

<div id="unlock">แตะหน้าจอหนึ่งครั้ง<br>เพื่อเริ่มระบบเสียง</div>

<div class="container">
    <div class="queue" id="queue">--</div>
    <div class="subtitle">เมนูที่สั่งได้แล้วค่ะ</div>
</div>

<script>
/* =======================
   setup
======================= */
const socket = io();
const queueEl = document.getElementById("queue");
const unlock = document.getElementById("unlock");

let unlocked = false;

/* =======================
   ระบบเสียงใหม่ (Web Speech API)
   แก้ไข: เสียงผู้หญิงไทย, ไม่พูดคำว่า "คิวที่/เชิญค่ะ"
======================= */
function speak(text) {
    if (!unlocked) return;

    // หยุดเสียงเก่าทันทีถ้ามีการกดเรียกซ้อน
    window.speechSynthesis.cancel();

    const msg = new SpeechSynthesisUtterance(text);
    msg.lang = 'th-TH';
    msg.rate = 0.9; // ความเร็วค่อนข้างปกติ ไม่เร็วเกินไป
    msg.pitch = 1.0;

    // ค้นหาเสียงผู้หญิงไทย
    const voices = window.speechSynthesis.getVoices();
    const femaleVoice = voices.find(v => 
        v.lang === 'th-TH' && (v.name.includes('Premium') || v.name.includes('Google') || v.name.includes('Female'))
    );
    
    if (femaleVoice) {
        msg.voice = femaleVoice;
    }

    window.speechSynthesis.speak(msg);
}

// โหลดรายการเสียง (จำเป็นสำหรับ Chrome/Safari)
window.speechSynthesis.onvoiceschanged = () => {
    window.speechSynthesis.getVoices();
};

unlock.addEventListener("click", () => {
    unlocked = true;
    unlock.style.display = "none";
    speak("เริ่มระบบค่ะ");
});

/* =======================
   เรียกคิว (แก้ให้ Real-Time เลขเปลี่ยนทันที)
======================= */
socket.on("call_queue", data => {
    // 🎯 1. อัปเดตตัวเลขบนจอทันที (แก้อาการดีเลย์ 1 ตำแหน่ง)
    queueEl.innerText = data.queue;
    queueEl.style.animation = "none";
    queueEl.offsetHeight; // force reflow
    queueEl.style.animation = "pop 0.4s ease-out";

    // 🎯 2. สั่งให้พูด (data.msg จาก app.py จะส่งมาแค่รหัสคิวเพียวๆ)
    speak(data.msg);
});

/* =======================
   ข้ามออร์เดอร์
======================= */
socket.on("speak_only", data => {
    speak(data.msg);
});

/* =======================
   อัปเดตหน้าจอปกติ (เช่น Reset หรือ อัปเดตจากจออื่น)
======================= */
socket.on("queue_updated", data => {
    if (data.current) {
        queueEl.innerText = data.current;
        // ถ้าเลขเปลี่ยน ให้ใส่แอนิเมชั่นด้วย
        if (data.current !== "--") {
            queueEl.style.animation = "none";
            queueEl.offsetHeight;
            queueEl.style.animation = "pop 0.4s ease-out";
        }
    }
});
</script>

</body>
</html>
