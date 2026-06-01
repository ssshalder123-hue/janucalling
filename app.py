from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import random

app = Flask(__name__)

# 🗄️ MongoDB Atlas Connection Setup
# এখানে তোমার নিজের MongoDB Connection URI বসাতে পারো, নিচে একটি ডেমো স্ট্যাবল কানেকশন দেওয়া হলো
try:
    client = MongoClient("mongodb+srv://testuser:testpass123@cluster0.mongodb.net/?retryWrites=true&w=majority", serverSelectionTimeoutMS=5000)
    db = client['janucalling_db']
    users_collection = db['users']
    rooms_collection = db['rooms']
    # কানেকশন টেস্ট
    client.server_info()
except Exception as e:
    print("MongoDB Error, switching to Local Memory Database:", e)
    # যদি মঙ্গোডিবি কানেক্ট না হয়, তবে অ্যাপ ক্র্যাশ করবে না, ব্যাকআপ লোকাল মেমোরি চালু হবে
    users_collection = {}
    rooms_collection = {}

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

    # ডেটাবেজ টাইপ চেক (MongoDB নাকি লোকাল ডিকশনারি)
    if isinstance(users_collection, dict):
        if phone in users_collection:
            return jsonify({"status": "error", "message": "Phone number already registered!"}), 400
        users_collection[phone] = {"name": name, "phone": phone, "gender": gender, "balance": 20, "status": "available" if gender == "female" else "offline"}
        user_data = users_collection[phone]
    else:
        if users_collection.find_one({"phone": phone}):
            return jsonify({"status": "error", "message": "Phone number already registered!"}), 400
        new_user = {"name": name, "phone": phone, "gender": gender, "balance": 20, "status": "available" if gender == "female" else "offline"}
        users_collection.insert_one(new_user)
        user_data = new_user

    return jsonify({
        "status": "success",
        "name": user_data["name"],
        "phone": user_data["phone"],
        "gender": user_data["gender"],
        "balance": user_data["balance"]
    })

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    phone = data.get('phone')

    if not phone:
        return jsonify({"status": "error", "message": "Phone number is required!"}), 400

    if isinstance(users_collection, dict):
        user = users_collection.get(phone)
    else:
        user = users_collection.find_one({"phone": phone})

    if not user:
        return jsonify({"status": "error", "message": "User not found! Please register first."}), 404

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

    if isinstance(users_collection, dict):
        if phone in users_collection:
            users_collection[phone]["status"] = status
            return jsonify({"status": "success"})
    else:
        if users_collection.find_one({"phone": phone}):
            users_collection.update_one({"phone": phone}, {"$set": {"status": status}})
            return jsonify({"status": "success"})
            
    return jsonify({"status": "error", "message": "User not found"}), 404

@app.route('/make_call', methods=['POST'])
def make_call():
    data = request.get_json() or {}
    boy_phone = data.get('phone')

    if isinstance(users_collection, dict):
        boy = users_collection.get(boy_phone)
        available_girls = [p for p, u in users_collection.items() if u["gender"] == "female" and u["status"] == "available"]
    else:
        boy = users_collection.find_one({"phone": boy_phone})
        available_girls = list(users_collection.find({"gender": "female", "status": "available"}))

    if not boy or boy["balance"] < 2:
        return jsonify({"status": "error", "message": "Insufficient balance (Min ₹2 required)!"}), 400

    if not available_girls:
        return jsonify({"status": "error", "message": "All hostings are currently busy or offline!"}), 404

    selected_girl = random.choice(available_girls)
    girl_phone = selected_girl if isinstance(users_collection, dict) else selected_girl["phone"]
    girl_name = users_collection[girl_phone]["name"] if isinstance(users_collection, dict) else selected_girl["name"]

    room_id = f"room_{int(random.random() * 1000000)}"

    if isinstance(rooms_collection, dict):
        rooms_collection[room_id] = {"boy_phone": boy_phone, "girl_phone": girl_phone, "status": "ringing"}
        users_collection[girl_phone]["status"] = "busy"
    else:
        rooms_collection.insert_one({"room_id": room_id, "boy_phone": boy_phone, "girl_phone": girl_phone, "status": "ringing"})
        users_collection.update_one({"phone": girl_phone}, {"$set": {"status": "busy"}})

    return jsonify({
        "status": "ringing",
        "room_id": room_id,
        "girl_name": girl_name,
        "girl_phone": girl_phone
    })

@app.route('/check_incoming', methods=['POST'])
def check_incoming():
    data = request.get_json() or {}
    phone = data.get('phone')

    if isinstance(rooms_collection, dict):
        for room_id, room in rooms_collection.items():
            if room["girl_phone"] == phone and room["status"] == "ringing":
                boy_name = users_collection[room["boy_phone"]]["name"]
                return jsonify({"incoming": True, "room_id": room_id, "boy_name": boy_name, "girl_phone": phone})
    else:
        room = rooms_collection.find_one({"girl_phone": phone, "status": "ringing"})
        if room:
            boy = users_collection.find_one({"phone": room["boy_phone"]})
            return jsonify({"incoming": True, "room_id": room["room_id"], "boy_name": boy["name"], "girl_phone": phone})

    return jsonify({"incoming": False})

@app.route('/accept_call', methods=['POST'])
def accept_call():
    data = request.get_json() or {}
    room_id = data.get('room_id')

    if isinstance(rooms_collection, dict):
        if room_id in rooms_collection:
            rooms_collection[room_id]["status"] = "connected"
            return jsonify({"status": "connected"})
    else:
        if rooms_collection.find_one({"room_id": room_id}):
            rooms_collection.update_one({"room_id": room_id}, {"$set": {"status": "connected"}})
            return jsonify({"status": "connected"})
            
    return jsonify({"status": "error"}), 404

@app.route('/deduct_minute', methods=['POST'])
def deduct_minute():
    data = request.get_json() or {}
    boy_phone = data.get('boy_phone')
    room_id = data.get('room_id')

    if isinstance(users_collection, dict):
        user = users_collection.get(boy_phone)
        if user and user["balance"] >= 2:
            users_collection[boy_phone]["balance"] -= 2
            return jsonify({"status": "success", "new_balance": users_db[boy_phone]["balance"]})
    else:
        user = users_collection.find_one({"phone": boy_phone})
        if user and user["balance"] >= 2:
            new_bal = user["balance"] - 2
            users_collection.update_one({"phone": boy_phone}, {"$set": {"balance": new_bal}})
            return jsonify({"status": "success", "new_balance": new_bal})
            
    return jsonify({"status": "low_balance"}), 400

@app.route('/end_call', methods=['POST'])
def end_call():
    data = request.get_json() or {}
    room_id = data.get('room_id')

    if isinstance(rooms_collection, dict):
        if room_id in rooms_collection:
            girl_phone = rooms_collection[room_id]["girl_phone"]
            users_collection[girl_phone]["status"] = "available"
            del rooms_collection[room_id]
            return jsonify({"status": "success"})
    else:
        room = rooms_collection.find_one({"room_id": room_id})
        if room:
            users_collection.update_one({"phone": room["girl_phone"]}, {"$set": {"status": "available"}})
            rooms_collection.delete_one({"room_id": room_id})
            return jsonify({"status": "success"})
            
    return jsonify({"status": "error"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
            
