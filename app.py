import os
import requests
from flask import Flask, request

BOT_TOKEN = os.getenv("7830666324:AAFofarBqKt9lIZDPGxsolG8TEHzIlueZpk")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    chat_id = data["message"]["chat"]["id"]
    message_text = data["message"].get("text", "")
    reply = f"Вы написали: {message_text}"
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": reply
    })
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Бот работает!"

if __name__ == "__main__":
    app.run()
