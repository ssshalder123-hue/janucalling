from flask import Flask, render_template, request, jsonify
import sqlite3
import random

app = Flask(__name__)
DATABASE = 'database.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # ইউজার টেবিল (টাকা/ব্যালেন্স হিসেবে হিসাব রাখার জন্য balance ব্যবহার হচ্ছে)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            name TEXT,
            gender TEXT,
            balance INTEGER DEFAULT 20,
            status TEXT DEFAULT 'offline'
        )
    ''')
    # একটি আলাদা কল ট্র্যাকিং টেবিল (লাইভ কল স্ট্যাটাস দেখার জন্য)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT UNIQUE,
            boy_phone TEXT,
            girl_phone TEXT,
            status TEXT DEFAULT 'ringing'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

# ১. রেজিস্ট্রেশন (নতুন কাস্টমারকে ২০ টাকা ফ্রি দেওয়া হলো, যাতে ১০ মিনিট কথা বলতে পারে)
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    phone = data.get('phone')
    name = data.get('name')
    gender = data.get('gender')

    if not phone or not name or not gender:
        return jsonify({"status": "error", "message": "সব তথ্য সঠিকভাবে দিন!"})

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        # ছেলেদের জন্য ২০ টাকা ফ্রি ব্যালেন্স
        initial_balance = 20 if gender == 'male' else 0
        cursor.execute("INSERT INTO users (phone, name, gender, balance, status) VALUES (?, ?, ?, ?, 'offline')", 
                       (phone, name, gender, initial_balance))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "রেজিস্ট্রেশন সফল!", "name": name, "phone": phone, "gender": gender, "balance": initial_balance})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "message": "এই নম্বরটি অলরেডি রেজিস্টার্ড! লগইন করুন।"})

# ২. লগইন
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    phone = data.get('phone')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, gender, balance FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"status": "success", "name": user[0], "gender": user[1], "balance": user[2], "phone": phone})
    return jsonify({"status": "error", "message": "অ্যাকাউন্ট পাওয়া যায়নি!"})

# ৩. হোস্টিং মেয়েদের অনলাইন/অফলাইন স্ট্যাটাস
@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    phone = data.get('phone')
    status = data.get('status')
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE phone = ?", (status, phone))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# ৪. কাস্টমার কল দিলে অনলাইন মেয়ে খোঁজা এবং সিগন্যাল তৈরি
@app.route('/make_call', methods=['POST'])
def make_call():
    data = request.get_json()
    boy_phone = data.get('phone')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE phone = ?", (boy_phone,))
    boy = cursor.fetchone()

    # প্রতি মিনিটে ২ টাকা কাটবে, তাই মিনিমাম ২ টাকা থাকা জরুরি
    if not boy or boy[0] < 2:
        conn.close()
        return jsonify({"status": "error", "message": "পর্যাপ্ত ব্যালেন্স নেই! প্রতি মিনিটে ২ টাকা কাটবে। রিচার্জ করুন।"})

    cursor.execute("SELECT phone, name FROM users WHERE gender = 'female' AND status = 'available'")
    available_girls = cursor.fetchall()

    if not available_girls:
        conn.close()
        return jsonify({"status": "error", "message": "এই মুহূর্তে কোনো হোস্টিং অনলাইন নেই!"})

    selected_girl = random.choice(available_girls)
    girl_phone = selected_girl[0]
    girl_name = selected_girl[1]

    room_id = f"room_{boy_phone}_{girl_phone}"
    
    # একটি লাইভ কল এন্ট্রি তৈরি করা হলো
    cursor.execute("INSERT OR REPLACE INTO active_calls (room_id, boy_phone, girl_phone, status) VALUES (?, ?, ?, 'ringing')",
                   (room_id, boy_phone, girl_phone))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "ringing",
        "room_id": room_id,
        "girl_phone": girl_phone,
        "girl_name": girl_name
    })

# ৫. মেয়েরা ব্যাকগ্রাউন্ডে এই API-তে প্রতি ৩ সেকেন্ড পর পর রিকোয়েস্ট পাঠাবে ইনকামিং কল চেক করতে
@app.route('/check_incoming', methods=['POST'])
def check_incoming():
    data = request.get_json()
    girl_phone = data.get('phone')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT room_id, boy_phone, users.name FROM active_calls JOIN users ON active_calls.boy_phone = users.phone WHERE girl_phone = ? AND active_calls.status = 'ringing'", (girl_phone,))
    call = cursor.fetchone()
    conn.close()

    if call:
        return jsonify({"incoming": True, "room_id": call[0], "boy_name": call[2]})
    return jsonify({"incoming": False})

# ৬. মেয়ে কল রিসিভ করলে স্ট্যাটাস 'connected' হবে
@app.route('/accept_call', methods=['POST'])
def accept_call():
    data = request.get_json()
    room_id = data.get('room_id')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE active_calls SET status = 'connected' WHERE room_id = ?", (room_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "connected"})

# ⏱️ ৭. কল চলাকালীন প্রতি ১ মিনিট পর পর কাস্টমারের ব্যালেন্স থেকে ২ টাকা কাটার মেকানিজম
@app.route('/deduct_minute', methods=['POST'])
def deduct_minute():
    data = request.get_json()
    boy_phone = data.get('boy_phone')
    room_id = data.get('room_id')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # প্রথমে কলটি এখনও লাইভ আছে কি না চেক করো
    cursor.execute("SELECT status FROM active_calls WHERE room_id = ?", (room_id,))
    call = cursor.fetchone()
    
    if not call or call[0] != 'connected':
        conn.close()
        return jsonify({"status": "disconnected"})

    # ব্যালেন্স ২ টাকা কমাও
    cursor.execute("UPDATE users SET balance = balance - 2 WHERE phone = ?", (boy_phone,))
    cursor.execute("SELECT balance FROM users WHERE phone = ?", (boy_phone,))
    new_balance = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    if new_balance < 2:
        return jsonify({"status": "low_balance", "new_balance": new_balance})
    return jsonify({"status": "success", "new_balance": new_balance})

# ৮. কল কেটে দিলে
@app.route('/end_call', methods=['POST'])
def end_call():
    data = request.get_json()
    room_id = data.get('room_id')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_calls WHERE room_id = ?", (room_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ended"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
