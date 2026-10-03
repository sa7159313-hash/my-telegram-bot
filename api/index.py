import os, requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
OWNER_ID = os.environ.get("OWNER_ID", "")

def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def redis_get(key):
    try:
        r = requests.get(f"{REDIS_URL}/get/{key}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=5)
        return r.json().get("result")
    except:
        return None

def redis_set(key, value):
    try:
        # Upstash REST needs URL encoded value
        requests.get(f"{REDIS_URL}/set/{key}/{value}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=5)
    except:
        pass

@app.route("/api/index", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    msg = data.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "")
    from_id = str(msg.get("from", {}).get("id", ""))

    if not chat_id or not text:
        return "ok"

    low = text.lower()

    # SAVE MEMORY
    if "shadow king" in low and ("yaad" in low or "mai" in low or "hu" in low):
        redis_set(f"owner:{from_id}", "SHADOW KING")
        if OWNER_ID:
            redis_set(f"owner:{OWNER_ID}", "SHADOW KING")
        send_msg(chat_id, "Haan Malik! Yaad kar liya, aap SHADOW KING ho 👑 Ab kabhi nahi bhulunga!")
        return "ok"

    # RECALL MEMORY
    if "mera naam" in low or "mai kaun" in low or "who am i" in low or "kaun hu" in low:
        name = redis_get(f"owner:{from_id}") or redis_get(f"owner:{OWNER_ID}")
        if name:
            send_msg(chat_id, f"Aap {name} ho Malik 👑")
        else:
            send_msg(chat_id, "Aap mere Malik ho! Naam batao, mai yaad rakh lunga KING!")
        return "ok"

    # Default
    send_msg(chat_id, f"Bolo Malik? Aapne bola: {text}")
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Bot is Live KING 👑"
