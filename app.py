from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import random

app = Flask(__name__)
DATABASE = 'database.db'

# ডাটাবেস তৈরি ও টেবিল সেটআপ
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # ইউজার টেবিল (ফোন নম্বর, নাম, জেন্ডার, ব্যালেন্স মিনিট, অনলাইন স্ট্যাটাস)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            phone TEXT PRIMARY KEY,
            name TEXT,
            gender TEXT,
            balance INTEGER DEFAULT 0,
            status TEXT DEFAULT 'offline'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')
    

# ১. রেজিস্ট্রেশন ও লগইন রুট
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    phone = data.get('phone')
    name = data.get('name')
    gender = data.get('gender') # 'male' অথবা 'female'

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()

    if not user:
        # নতুন ইউজার হলে ডাটাবেসে সেভ হবে
        cursor.execute("INSERT INTO users (phone, name, gender, balance, status) VALUES (?, ?, ?, ?, ?)",
                       (phone, name, gender, 0 if gender == 'male' else 0, 'offline'))
        conn.commit()
    
    conn.close()
    return jsonify({"status": "success", "message": "Logged in successfully", "phone": phone})

# ২. মেয়েদের (Hosting) অনলাইন/অফলাইন স্ট্যাটাস আপডেট
@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    phone = data.get('phone')
    status = data.get('status') # 'available', 'busy', 'offline'

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE phone = ?", (status, phone))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Status updated to {status}"})

# ৩. ছেলেদের জন্য অটোমেটিক কল কানেক্ট লজিক
@app.route('/connect_call', methods=['POST'])
def connect_call():
    data = request.get_json()
    boy_phone = data.get('phone')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # ছেলের ব্যালেন্স চেক করো
    cursor.execute("SELECT balance FROM users WHERE phone = ?", (boy_phone,))
    boy = cursor.fetchone()

    if not boy or boy[0] <= 0:
        conn.close()
        return jsonify({"status": "error", "message": "Insufficient balance! Please recharge."})

    # এই মুহূর্তে কোন মেয়েরা 'available' বা অনলাইন আছে তাদের খোঁজো
    cursor.execute("SELECT phone, name FROM users WHERE gender = 'female' AND status = 'available'")
    available_girls = cursor.fetchall()

    if not available_girls:
        conn.close()
        return jsonify({"status": "error", "message": "All hostings are busy or offline. Try again in a moment!"})

    # অনলাইন মেয়েদের মধ্য থেকে যেকোনো একজনকে অটোমেটিক র‍্যান্ডমলি বেছে নাও
    selected_girl = random.choice(available_girls)
    girl_phone = selected_girl[0]
    girl_name = selected_girl[1]

    # দুজনের স্ট্যাটাস 'busy' করে দাও যাতে অন্য কেউ কল না পায়
    cursor.execute("UPDATE users SET status = 'busy' WHERE phone = ?", (boy_phone,))
    cursor.execute("UPDATE users SET status = 'busy' WHERE phone = ?", (girl_phone,))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "connected",
        "message": "Call connected successfully!",
        "girl_name": girl_name,
        "channel_id": f"room_{boy_phone}_{girl_phone}" # Agora-র জন্য ইউনিক রুম আইডি
    })

# ৪. সিক্রেট অ্যাডমিন প্যানেল (তুমি কাস্টমারকে মিনিট রিচার্জ করে দেওয়ার জন্য)
@app.route('/admin/recharge', methods=['POST'])
def admin_recharge():
    data = request.get_json()
    target_phone = data.get('phone')
    minutes_to_add = int(data.get('minutes'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE phone = ?", (minutes_to_add, target_phone))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Successfully added {minutes_to_add} minutes to {target_phone}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
