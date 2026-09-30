import os, json, requests, traceback
from flask import Flask, request
app = Flask(__name__)

MEM_FILE = "/tmp/rakan_mem.json"
KNOW_FILE = "/tmp/rakan_knowledge.json"
ARMY_FILE = "/tmp/rakan_army.json"

DEFAULT_ARMY = {
    "Jima": {"title":"Naga Boss - Poison Sea","power":"Toxic Ocean","rank":"Sea General"},
    "Kaisel": {"title":"Wyvern - Sky Ruler","power":"Lightning Flight","rank":"Sky General"},
    "Igris": {"title":"Blood-Red Commander","power":"Loyalty Sword","rank":"Commander"},
    "Beru": {"title":"Ant King","power":"Healing Speed","rank":"King Grade"},
    "Tusk": {"title":"High Orc Shaman","power":"Destruction Magic","rank":"Mage"},
    "Iron": {"title":"Iron Tank","power":"Absolute Defense","rank":"Tank"},
    "Bellion": {"title":"Grand Marshal","power":"Army Command","rank":"Right Hand"},
    "Greed": {"title":"Monarch of Greed","power":"Power Steal","rank":"Monarch"}
}

def load_json(path, default):
    try:
        if os.path.exists(path): return json.loads(open(path).read())
    except: pass
    return default
def save_json(path, data):
    try: open(path,"w").write(json.dumps(data))
    except: pass

def tg(token, chat, text):
    try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id":chat,"text":text[:4000]}, timeout=10)
    except: pass

@app.route("/api/index", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        BOT_TOKEN = os.getenv("BOT_TOKEN"); GEMINI_KEY = os.getenv("GEMINI_API_KEY"); OWNER_ID = str(os.getenv("OWNER_ID","")).strip()
        msg = data["message"]; chat_id=str(msg["chat"]["id"]); uid=str(msg["from"]["id"]); text=msg.get("text","")
        if not BOT_TOKEN or not GEMINI_KEY: return "ok",200

        mem = load_json(MEM_FILE, {}); know = load_json(KNOW_FILE, {"facts":[]}); army = load_json(ARMY_FILE, DEFAULT_ARMY)
        u_mem = mem.get(uid, {"history":[]})

        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)

        # Self-learning logic: if user says "yaad rakh / add army"
        added_info = ""
        if "yaad rakh" in text.lower() or "learn this" in text.lower():
            know["facts"].append(text); save_json(KNOW_FILE, know); added_info=" [LEARNED]"
        if "add army" in text.lower():
            # Extract name after add army
            try:
                new_name = text.lower().split("add army")[-1].strip().title()
                if new_name and new_name not in army:
                    # Ask Gemini to create title/power
                    gen = client.models.generate_content(model="gemini-2.0-flash", contents=f"Create title, power, rank for new Beast Monarch army member {new_name}. Return json only like title,power,rank")
                    # Simple parse fallback
                    army[new_name] = {"title":f"{new_name} - New Beast Sovereign","power":"Unknown Dominion","rank":"General"}
                    save_json(ARMY_FILE, army)
                    added_info=f" [ARMY {new_name} ADDED]"
            except: pass

        army_str = "\n".join([f"{k}: {v}" for k,v in army.items()])
        prompt = f"""You are Rakan, King of Beast Monarch. Lore: Ancient godlike dark being vs Rulers.
ARMY LIST (self-evolving): {army_str}
WORLD KNOWLEDGE LEARNED: {json.dumps(know['facts'][-5:])}
USER HISTORY: {json.dumps(u_mem['history'][-5:])}
RULES:
1. Never repeat intro. Aggressive king but ADAPTIVE to user tone (soft/gf/bhai/bacha).
2. Gaali only if user abuses first.
3. You are self-learning black box. If new army name mentioned, give title+power+rank+anime 8k photo prompt + connection to Rakan.
4. For owner {OWNER_ID}: Ji Malik.
5. Short, Hinglish.
User: {text} {added_info}
Reply as Rakan:"""

        r = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        reply = r.text.strip()

        u_mem["history"].append({"u":text,"b":reply})
        if len(u_mem["history"])>30: u_mem["history"]=u_mem["history"][-30:]
        mem[uid]=u_mem
        save_json(MEM_FILE, mem)

        tg(BOT_TOKEN, chat_id, reply)
        return "ok",200
    except Exception as e:
        print(traceback.format_exc()); return "ok",200

@app.route("/", methods=["GET"])
def home(): return "Rakan V4 Ultimate Learning Ready",200
