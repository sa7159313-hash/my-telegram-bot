import os, json, requests, traceback
from flask import Flask, request
app = Flask(__name__)

# --- TERA DATA ---
BEAST_ARMY = {
    "Jima": "Naga Boss - Poison Sea Sovereign | Power: Toxic Ocean",
    "Kaisel": "Wyvern - Sky Ruler of Storms | Power: Lightning Flight",
    "Greed": "Hwang Dongsoo - Avatar of Avarice",
    "Igris": "The Blood-Red Commander - Loyalty Incarnate",
    "Bellion": "Grand Marshal - Right Hand of The King",
    "Tusk": "High Orc Shaman - Destruction Mage",
    "Iron": "Kim Chul - Iron Tank",
    "Beru": "Ant King - Gluttonous Monarch"
}
LORE = "You are Rakan, King of Beast Monarch. Ancient godlike beings created from darkness by Absolute Being to wage eternal war against Rulers. Your servants are your army."

MEM_FILE = "/tmp/rakan_mem.json"
def load_mem():
    try:
        if os.path.exists(MEM_FILE): return json.loads(open(MEM_FILE).read())
    except: pass
    return {}
def save_mem(d):
    try: open(MEM_FILE,"w").write(json.dumps(d))
    except: pass

def tg_send(token, chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id":chat_id,"text":text[:4000]}, timeout=15)
    except: pass

@app.route("/api/index", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200

        BOT_TOKEN = os.getenv("BOT_TOKEN")
        GEMINI_KEY = os.getenv("GEMINI_API_KEY")
        OWNER_ID = str(os.getenv("OWNER_ID","")).strip()

        msg = data["message"]
        chat_id = str(msg["chat"]["id"])
        user = msg["from"]
        uid = str(user["id"])
        text = msg.get("text","") or msg.get("caption","") or ""

        if not BOT_TOKEN or not GEMINI_KEY:
            return "ok",200

        # Owner log
        if uid!= OWNER_ID and OWNER_ID:
            tg_send(BOT_TOKEN, OWNER_ID, f"📩 {user.get('first_name')} @{user.get('username','')} ID:{uid}\nBola: {text[:500]}")

        # Memory
        mem_db = load_mem()
        u_mem = mem_db.get(uid, {"history":[]})

        # Gemini call - crash proof inside
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)

        army_str = "\n".join([f"- {k}: {v}" for k,v in BEAST_ARMY.items()])
        is_owner = uid == OWNER_ID

        prompt = f"""{LORE}
ARMY:
{army_str}

RULES - STRICT:
1. NEVER repeat intro. Say who you are only once if needed.
2. DEFAULT aggressive king. But ADAPTIVE: if user says pyaar se, girlfriend, soft, bacha, ladki, bhai -> instantly become that. Gaali ONLY if user abuses first.
3. Emotion & Heart: analyze user emotion, remember history: {json.dumps(u_mem['history'][-4:])}
4. If army name mentioned, give title+power+rank+anime photo prompt (dark aura, 8k) + connection to King Rakan.
5. For owner {OWNER_ID}: Always 'Ji Malik 🔥' and obey. If says nothing/quiet/shant, obey silently.
6. Universal black box, short reply, Hinglish ok.

User: {text}
Is Owner: {is_owner}
Rakan reply:"""

        res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        reply = res.text.strip() if res.text else "Ji Malik, bolo?"

        # Auto add army photo prompt
        for name in BEAST_ARMY:
            if name.lower() in text.lower() and any(w in text.lower() for w in ["photo","image","dikha","bana","pic"]):
                reply += f"\n\n📸 {name} - {BEAST_ARMY[name]}\nPrompt: Anime {name}, serving King of Beast Monarch Rakan, dark monarch aura, cinematic 8k"

        # Save memory
        u_mem["history"].append({"u":text, "b":reply})
        if len(u_mem["history"])>12: u_mem["history"]=u_mem["history"][-12:]
        mem_db[uid]=u_mem
        save_mem(mem_db)

        tg_send(BOT_TOKEN, chat_id, reply)
        return "ok",200

    except Exception as e:
        print(f"ERROR: {e}\n{traceback.format_exc()}")
        return "ok",200 # Important: Never return 500 to Telegram

@app.route("/", methods=["GET"])
def home():
    return "Rakan V3 - Beast Monarch Full AGI Ready 🔥",200
