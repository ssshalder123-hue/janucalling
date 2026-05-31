from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = "mongodb+srv://USERNAME:PASSWORD@cluster0.qihz36g.mongodb.net/janudating"

client = MongoClient(MONGO_URI)

db = client["janudating"]
users = db["users"]

@app.route("/")
def home():
    return "Janu Dating App Running"

@app.route("/register", methods=["POST"])
def register():

    data = request.json

    user = {
        "name": data.get("name"),
        "phone": data.get("phone"),
        "gender": data.get("gender"),
        "password": data.get("password")
    }

    users.insert_one(user)

    return jsonify({
        "success": True,
        "message": "Registration Successful"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
