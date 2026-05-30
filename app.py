from flask import Flask, render_template, request, jsonify
import sqlite3
import random

app = Flask(__name__)
DATABASE = 'database.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # ইউজার টেবিল আপডেট (হোয়াটসঅ্যাপ নম্বর ট্র্যাক করার জন্য)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            name TEXT,
            gender TEXT,
            balance INTEGER DEFAULT 10,
            status TEXT DEFAULT 'offline'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

# ১. রেজিস্ট্রেশন
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
        cursor.execute("INSERT INTO users (phone, name, gender, balance, status) VALUES (?, ?, ?, 10, 'offline')", 
                       (phone, name, gender))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "রেজিস্ট্রেশন সফল! ১০ মিনিট ফ্রি দেওয়া হয়েছে।", "name": name, "phone": phone, "gender": gender, "balance": 10})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "message": "এই নম্বরটি অলরেডি আছে! লগইন করুন।"})

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
    return jsonify({"status": "error", "message": "অ্যাকাউন্ট পাওয়া যায়নি! প্রথমে রেজিস্ট্রেশন করুন।"})

# ৩. স্ট্যাটাস আপডেট
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

# ৪. হোয়াটসঅ্যাপ কল কানেক্ট ও ব্যালেন্স কাটা
@app.route('/connect_call', methods=['POST'])
def connect_call():
    data = request.get_json()
    boy_phone = data.get('phone')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE phone = ?", (boy_phone,))
    boy = cursor.fetchone()

    if not boy or boy[0] <= 0:
        conn.close()
        return jsonify({"status": "error", "message": "আপনার ব্যালেন্স শেষ! দয়া করে রিচার্জ করুন।"})

    # অনলাইন হোস্টিং মেয়েদের খোঁজা
    cursor.execute("SELECT phone, name FROM users WHERE gender = 'female' AND status = 'available'")
    available_girls = cursor.fetchall()

    if not available_girls:
        conn.close()
        return jsonify({"status": "error", "message": "এই মুহূর্তে কোনো হোস্টিং অনলাইন নেই। একটু পরে চেষ্টা করুন!"})

    selected_girl = random.choice(available_girls)
    girl_phone = selected_girl[0]
    girl_name = selected_girl[1]

    # কল প্রতি ১ মিনিট কেটে নেওয়া হচ্ছে
    new_balance = boy[0] - 1
    cursor.execute("UPDATE users SET balance = ? WHERE phone = ?", (new_balance, boy_phone))
    conn.commit()
    conn.close()

    # হোয়াটসঅ্যাপে সরাসরি মেসেজসহ চ্যাট খোলার লিঙ্ক
    whatsapp_link = f"https://wa.me/{girl_phone}?text=Hello%20{girl_name},%20I%20am%20calling%20you%20from%20Janu%20Calling%20App!"

    return jsonify({
        "status": "connected",
        "girl_name": girl_name,
        "new_balance": new_balance,
        "whatsapp_link": whatsapp_link
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
