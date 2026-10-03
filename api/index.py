import os, requests, json
from flask import Flask, request

app = Flask(__name__)

REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
OWNER_ID = str(os.environ.get("OWNER_ID", ""))

def redis_get(key):
    r = requests.get(f"{REDIS_URL}/get/{key}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"})
    try: return r.json().get("result")
    except: return None

def redis_set(key, value):
    requests.post(f"{REDIS_URL}/set/{key}/{value}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"})

def redis_set_json(key, data):
    # store as string
    val = json.dumps(data).replace(" ", "%20")
    requests.get(f"{REDIS_URL}/set/{key}/{val}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"})

@app.route('/api/index', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data: return "ok"
    
    msg = data.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "").lower()
    from_id = str(msg.get("from", {}).get("id", ""))

    if not chat_id: return "ok"

    # MEMORY LOGIC - NEVER FORGET
    if "shadow king" in text or "yaad rakh" in text:
        redis_set(f"owner:{from_id}:name", "SHADOW KING")
        redis_set(f"owner:{OWNER_ID}:name", "SHADOW KING")
        send_msg(chat_id, "Haan Malik! Yaad kar liya, aap SHADOW KING ho 👑 Ab kabhi nahi bhulunga!")
        return "ok"

    # Check memory
    saved_name = redis_get(f"owner:{from_id}:name") or redis_get(f"owner:{OWNER_ID}:name")
    
    if "mera naam" in text or "mai kaun" in text or "who am i" in text:
        if saved_name:
            send_msg(chat_id, f"Aap {saved_name} ho Malik 👑")
        else:
            send_msg(chat_id, "Aap mere Malik ho, naam batao mai yaad rakh lunga!")
        return "ok"

    # Normal reply logic (Gemini call here)
    return "ok"

def send_msg(chat_id, text):
    token = os.environ.get("BOT_TOKEN")
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": text})

# Vercel entry
app = app
