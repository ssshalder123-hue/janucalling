from flask import Flask, render_template, request, jsonify
import sqlite3
import random

app = Flask(__name__)
DATABASE = 'database.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # ইউজার টেবিল (ব্যালেন্স ডিফল্ট ১০ মিনিট ফ্রি দেওয়া হলো নতুন রেজিস্ট্রেশনে)
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

# ১. নতুন ইউজার রেজিস্ট্রেশন (১০ মিনিট ফ্রি ব্যালেন্সসহ)
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
        # নতুন ইউজারকে ১০ মিনিট ফ্রি ব্যালেন্স দিয়ে সেভ করা হচ্ছে
        cursor.execute("INSERT INTO users (phone, name, gender, balance, status) VALUES (?, ?, ?, 10, 'offline')", 
                       (phone, name, gender))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "রেজিস্ট্রেশন সফল হয়েছে!", "name": name, "phone": phone, "gender": gender, "balance": 10})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "message": "এই মোবাইল নম্বরটি অলরেডি রেজিস্টার্ড! দয়া করে লগইন করুন।"})

# ২. পুরোনো ইউজার লগইন (নম্বর দিয়ে আগের ডেটা আনা)
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    phone = data.get('phone')

    if not phone:
        return jsonify({"status": "error", "message": "মোবাইল নম্বর দিন!"})

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, gender, balance FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({
            "status": "success", 
            "name": user[0], 
            "gender": user[1], 
            "balance": user[2],
            "phone": phone
        })
    else:
        return jsonify({"status": "error", "message": "এই নম্বরে কোনো অ্যাকাউন্ট নেই! প্রথমে রেজিস্ট্রেশন করুন।"})

# ৩. মেয়েদের অনলাইন/অফলাইন স্ট্যাটাস আপডেট
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

# ৪. ছেলেদের অটো-কানেক্ট কল সিস্টেম (ব্যালেন্স চেকসহ)
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

    # অনলাইন থাকা মেয়েদের খোঁজা হচ্ছে
    cursor.execute("SELECT phone, name FROM users WHERE gender = 'female' AND status = 'available'")
    available_girls = cursor.fetchall()

    if not available_girls:
        conn.close()
        return jsonify({"status": "error", "message": "এই মুহূর্তে কোনো হোস্টিং অনলাইন নেই। দয়া করে একটু পরে চেষ্টা করুন!"})

    selected_girl = random.choice(available_girls)
    girl_phone = selected_girl[0]
    girl_name = selected_girl[1]

    # কল কানেক্ট হলে ১ মিনিট কেটে নেওয়া হচ্ছে টেস্ট হিসেবে
    new_balance = boy[0] - 1
    cursor.execute("UPDATE users SET balance = ? WHERE phone = ?", (new_balance, boy_phone))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "connected",
        "girl_name": girl_name,
        "new_balance": new_balance,
        "channel_id": f"room_{boy_phone}_{girl_phone}"
    })

# ৫. অ্যাডমিন রিচার্জ সিস্টেম
@app.route('/admin_recharge', methods=['POST'])
def admin_recharge():
    data = request.get_json()
    target_phone = data.get('phone')
    minutes_to_add = int(data.get('minutes'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE phone = ?", (minutes_to_add, target_phone))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"সফলভাবে {minutes_to_add} মিনিট যোগ করা হয়েছে।"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
