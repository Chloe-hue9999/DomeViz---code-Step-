from flask import Flask, render_template, send_from_directory, request
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import random
import socket  # 新加: 获取IP
import qrcode  # 新加: 生成QR
import os  # 新加: 文件路径

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Simulated Objects
OBJECTS = [
    {"id": "ZTF-2024-A", "type": "Supernova"},
    {"id": "ZTF-2024-B", "type": "Asteroid"},
    {"id": "ZTF-2024-C", "type": "Variable Star"},
]

# INITIAL STATE
state = {
    "object_id": OBJECTS[0]["id"],
    "votes": {"real": 0, "bogus": 0},
    "stage": "show",
    "connected_users": 0
}

# MEMORY TO TRACK WHO VOTED
voted_users = set()

# 生成QR码
def generate_qr():
    # 获取本机的实际局域网IP（不是127.0.0.1，这样手机才能访问）
    try:
        # 通过连接外部地址获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        # 备选方案
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except:
            local_ip = "127.0.0.1"
    
    # 如果仍然是环回地址，尝试其他方法
    if local_ip.startswith('127.'):
        import subprocess
        try:
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='gbk')
            lines = result.stdout.split('\n')
            for line in lines:
                if 'IPv4' in line and '192.' in line or '10.' in line or '172.' in line:
                    local_ip = line.split(':')[-1].strip()
                    break
        except:
            pass
    
    phone_url = f"http://{local_ip}:5000/phone"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(phone_url)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    if not os.path.exists('static'):
        os.makedirs('static')
    img.save('static/qr_code.png')
    print(f"[OK] QR Code generated")
    print(f"[OK] Phone URL: {phone_url}")
    print(f"[OK] Local IP: {local_ip}")
    print(f"[OK] If scan doesn't work, try: http://{local_ip}:5000/phone")

@app.route("/")
def dome():
    return render_template("dome.html")

@app.route("/phone")
def phone():
    return render_template("phone.html")

# NEW: Separate page for the Presenter
@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)  # 新加: 静态文件如QR

@socketio.on("connect")
def handle_connect():
    # increment count and broadcast updated state
    state["connected_users"] += 1
    emit("update", state, broadcast=True)

@socketio.on("vote")
def handle_vote(data):
    # Accept votes in any stage (remove the stage check for testing)
    # if state["stage"] != "voting":
    #     print("Voting is not open yet.")
    #     emit("vote_error", {"msg": "Voting is not open yet."})
    #     return
    if request.sid in voted_users:
        print(f"User {request.sid} tried to vote twice! Ignored.")
        emit("vote_error", {"msg": "You have already voted."})
        return
    choice = data.get("choice")
    if choice in state["votes"]:
        state["votes"][choice] += 1
        voted_users.add(request.sid)
        print(f"Vote received: {choice}")
        print(f"Current state: {state}")
        emit("update", state, broadcast=True)
        emit("vote_confirmed")
    else:
        print(f"Invalid choice: {choice}")
        emit("vote_error", {"msg": f"Invalid choice: {choice}"})


@socketio.on("advance_stage")
def advance_stage():
    current = state["stage"]
    if current == "show":
        state["stage"] = "voting"
    elif current == "voting":
        state["stage"] = "reveal"
    elif current == "reveal":
        state["stage"] = "show"
        state["votes"] = {"real": 0, "bogus": 0}
        voted_users.clear()
        new_obj = random.choice(OBJECTS)
        state["object_id"] = new_obj["id"]
    emit("update", state, broadcast=True)


@socketio.on("disconnect")
def handle_disconnect(data=None):
    # decrement connected user count
    state["connected_users"] = max(0, state.get("connected_users", 1) - 1)
    emit("update", state, broadcast=True)


if __name__ == "__main__":
    generate_qr()  # 调用生成QR
    # 端口可以通过环境变量设置，避免5000冲突
    port = int(os.environ.get("DOME_PORT", 5000))
    try:
        print(f"Starting server on 0.0.0.0:{port} ...")
        socketio.run(app, host="0.0.0.0", port=port, debug=False)
    except OSError as e:
        print("Failed to start server:", e)
        print("Try changing the DOME_PORT environment variable or free the port.")
        raise
