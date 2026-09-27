from flask import Flask, request
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

@app.route('/')
def home():
    return "Bot is Running! KING is here!"

@app.route('/api/index', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        data = request.json
        print(data)
        return {"ok": True}
    return "Bot Webhook Ready"

# Vercel needs this
app = app