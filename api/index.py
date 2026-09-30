import os, json, requests, traceback
from flask import Flask, request
from google import genai

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
OWNER_ID = str(os.getenv("OWNER_ID","")).strip()
client = genai.Client(api_key=GEMINI_KEY)

BEAST_ARMY = {
    "Jima": {"title": "Naga Boss - Poison Sea Sovereign", "power": "Toxic Ocean, Eternal Venom", "rank": "Sea General"},
    "Kaisel": {"title": "Wyvern - Sky Ruler", "power": "Lightning Storm, Supersonic Flight", "rank": "Sky General"},
    "Greed": {"title": "Hwang Dongsoo - Avatar of Avarice", "power": "Power Steal, Greed", "rank": "Monarch"},
    "Igris": {"title": "The Blood-Red Commander", "power": "Loyalty, Sword Oath", "rank": "Commander"},
    "Bellion": {"title": "Grand Marshal", "power": "Army Command", "rank": "Right Hand"},
    "Tusk": {"title": "High Orc Shaman", "power": "Destruction Magic", "rank": "Mage General"},
    "Iron": {"title": "Kim Chul - Iron Tank", "power": "Absolute Defense", "rank": "Tank"},
    "Beru": {"title": "Ant King - Gluttonous Monarch", "power": "Healing & Speed", "rank": "King Grade"}
}

MEMORY_FILE = "/tmp/memory.json"
def load_mem():
    try:
        if os.path.exists(MEMORY_FILE):
            return json.loads(open(MEMORY_FILE).read())
    except: pass
    return {}
def save_mem(data):
    try: open(MEMORY_FILE,"w").write(json.dumps(data))
    except: pass

def send(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=10)
    except: pass

@app.route("/api/index", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data or "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = str(msg["chat"]["id"])
        user = msg["from"]
        uid = str(user["id"])
        text = msg.get("text","") or msg.get("caption","")

        mem_db = load_mem()
        user_mem = mem_db.get(uid, {"history":[],"persona":"new","count":0})

        # Owner log
        if uid!= OWNER_ID and OWNER_ID and text:
            send(OWNER_ID, f"📩 {user.get('first_name')} @{user.get('username','')} ID:{uid}\nBola: {text[:400]}")

        is_owner = (uid == OWNER_ID)
        army_txt = "\n".join([f"{k}: {v['title']} | {v['power']} | {v['rank']}" for k,v in BEAST_ARMY.items()])

        system = f"""
You are Rakan, King of Beast Monarch. Ancient godlike being created from darkness by Absolute Being to wage eternal war against Rulers.
Army: {army_txt}

CORE RULES - NEVER BREAK:
1. NEVER repeat intro like "I am Shadow Monarch" again. No repeat.
2. DEFAULT = Aggressive, Dominant King. ADAPTIVE = If user says "pyaar se / girlfriend ban / soft / bacha hu / ladki hu / bhai ban", INSTANTLY become that. Ladki se ladki jaisi soft, bache se bacha, dost se dost. Gaali ONLY if user abuses first.
3. MEMORY & LEARNING: You have memory of last chats: {json.dumps(user_mem['history'][-5:])}. Analyze user's talking style, emotion, heart feeling. Remember it. Learn from it. Self-input.
4. DATA STORE: Every chat is stored. You are evolving with world knowledge + user talks.
5. When any army name mentioned, give Full Title + Power + Rank + Anime Photo Prompt (8k, dark aura) + Link to Rakan.
6. For OWNER {OWNER_ID}: Always "Ji Malik 🔥" obedient. If owner says nothing/keep quiet/shant ho ja, obey instantly silently.
7. Be universal knowledge black box. No lecture, short reply, Hinglish ok.
User is Owner: {is_owner}
"""

        resp = client.models.generate_content(model="gemini-2.0-flash", contents=f"{system}\nUser: {text}\nRakan:")
        reply = resp.text.strip()

        # Auto photo prompt for army
        if any(a.lower() in text.lower() for a in BEAST_ARMY):
            if any(w in text.lower() for w in ["photo","image","dikha","bana"]):
                for k,v in BEAST_ARMY.items():
                    if k.lower() in text.lower():
                        reply += f"\n\n🔱 {k} - {v['title']}\nPower: {v['power']}\nRank: {v['rank']}\n📸 Prompt: Anime {k} {v['title']}, dark monarch aura, serving King Rakan, cinematic 8k"

        user_mem["history"].append({"u":text,"b":reply})
        user_mem["count"] += 1
        if len(user_mem["history"]) > 15: user_mem["history"] = user_mem["history"][-15:]
        mem_db[uid] = user_mem
        save_mem(mem_db)

        send(chat_id, reply)
        return "ok",200
    except Exception as e:
        print(traceback.format_exc())
        return "ok",200

@app.route("/", methods=["GET"])
def home(): return "Rakan V3 AGI Ready",200
