from flask import Flask, render_template, request, jsonify
import random

app = Flask(__name__)

# ইন-মেমোরি ডেটাবেস (রেন্ডার সার্ভার ২৪ ঘণ্টা ডেটা মেমোরিতে রাখবে)
users_db = {}
active_rooms = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name')
    phone = data.get('phone')
    gender = data.get('gender')

    if not name or not phone or not gender:
        return jsonify({"status": "error", "message": "All fields are required!"}), 400

    if phone in users_db:
        return jsonify({"status": "error", "message": "Phone number already registered! Please login."}), 400

    # নতুন অ্যাকাউন্ট তৈরির সাথে সাথে ₹২০ ফ্রি ব্যালেন্স
    users_db[phone] = {
        "name": name,
        "phone": phone,
        "gender": gender,
        "balance": 20,
        "status": "available" if gender == "female" else "offline"
    }

    return jsonify({
        "status": "success",
        "message": "Registration successful!",
        "name": name,
        "phone": phone,
        "gender": gender,
        "balance": users_db[phone]["balance"]
    })

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    phone = data.get('phone')

    if not phone:
        return jsonify({"status": "error", "message": "Phone number is required!"}), 400

    if phone not in users_db:
        return jsonify({"status": "error", "message": "User not found! Please register first."}), 404

    user = users_db[phone]
    return jsonify({
        "status": "success",
        "name": user["name"],
        "phone": user["phone"],
        "gender": user["gender"],
        "balance": user["balance"]
    })

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json() or {}
    phone = data.get('phone')
    status = data.get('status')

    if phone in users_db:
        users_db[phone]["status"] = status
        return jsonify({"status": "success", "message": f"Status updated to {status}"})
    return jsonify({"status": "error", "message": "User not found"}), 404

@app.route('/make_call', methods=['POST'])
def make_call():
    data = request.get_json() or {}
    boy_phone = data.get('phone')

    if boy_phone not in users_db:
        return jsonify({"status": "error", "message": "Unauthorized user"}), 401

    if users_db[boy_phone]["balance"] < 2:
        return jsonify({"status": "error", "message": "Insufficient balance! Please recharge."}), 400

    # অনলাইনে থাকা ফিমেল হোস্ট খোঁজা
    available_girls = [p for p, u in users_db.items() if u["gender"] == "female" and u["status"] == "available"]

    if not available_girls:
        return jsonify({"status": "error", "message": "All models are busy or offline!"}), 404

    selected_girl_phone = random.choice(available_girls)
    girl_user = users_db[selected_girl_phone]

    # অডিও কলের জন্য ইউনিক চ্যানেল নেম (Agora Channel)
    room_id = f"room_{int(random.random() * 1000000)}"

    active_rooms[room_id] = {
        "boy_phone": boy_phone,
        "girl_phone": selected_girl_phone,
        "status": "ringing"
    }

    users_db[selected_girl_phone]["status"] = "busy"

    return jsonify({
        "status": "ringing",
        "room_id": room_id,
        "girl_name": girl_user["name"],
        "girl_phone": selected_girl_phone
    })

@app.route('/check_incoming', methods=['POST'])
def check_incoming():
    data = request.get_json() or {}
    phone = data.get('phone')

    for room_id, room in active_rooms.items():
        if room["girl_phone"] == phone and room["status"] == "ringing":
            boy_name = users_db[room["boy_phone"]]["name"]
            return jsonify({
                "incoming": True,
                "room_id": room_id,
                "boy_name": boy_name
            })
    return jsonify({"incoming": False})

@app.route('/accept_call', methods=['POST'])
def accept_call():
    data = request.get_json() or {}
    room_id = data.get('room_id')

    if room_id in active_rooms:
        active_rooms[room_id]["status"] = "connected"
        return jsonify({"status": "connected"})
    return jsonify({"status": "error", "message": "Call expired"}), 404

@app.route('/deduct_minute', methods=['POST'])
def deduct_minute():
    data = request.get_json() or {}
    boy_phone = data.get('boy_phone')
    room_id = data.get('room_id')

    if room_id not in active_rooms or boy_phone not in users_db:
        return jsonify({"status": "error", "message": "Call ended"}), 404

    if users_db[boy_phone]["balance"] >= 2:
        users_db[boy_phone]["balance"] -= 2
        return jsonify({"status": "success", "new_balance": users_db[boy_phone]["balance"]})
    return jsonify({"status": "low_balance"}), 400

@app.route('/end_call', methods=['POST'])
def end_call():
    data = request.get_json() or {}
    room_id = data.get('room_id')

    if room_id in active_rooms:
        girl_phone = active_rooms[room_id]["girl_phone"]
        if girl_phone in users_db:
            users_db[girl_phone]["status"] = "available"
        del active_rooms[room_id]
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
