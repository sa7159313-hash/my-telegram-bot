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
    "Beru": {"title":"Ant King","power":"Gluttonous Speed","rank":"King Grade"},
    "Tusk": {"title":"High Orc Shaman","power":"Destruction Magic","rank":"Mage"},
    "Iron": {"title":"Iron Tank","power":"Absolute Defense","rank":"Tank"},
    "Bellion": {"title":"Grand Marshal","power":"Army Command","rank":"Right Hand"},
    "Greed": {"title":"Monarch of Greed","power":"Power Steal","rank":"Monarch"}
}

def load_json(path, default):
    try:
        if os.path.exists(path): return json.loads(open(path).read())
    except Exception as e:
        print(f"LOAD_ERR {path}: {e}")
    return default

def save_json(path, data):
    try: open(path,"w").write(json.dumps(data))
    except Exception as e: print(f"SAVE_ERR {path}: {e}")

def tg_send(token, chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id":chat_id,"text":text[:4000]}, timeout=15)
        print(f"TG_SEND -> {chat_id} Status:{r.status_code} Resp:{r.text[:300]}")
        return r.status_code == 200
    except Exception as e:
        print(f"TG_SEND_ERROR: {e}")
        return False

@app.route("/api/index", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data:
            print("NO_MESSAGE_FIELD")
            return "ok",200

        BOT_TOKEN = os.getenv("BOT_TOKEN","").strip()
        GEMINI_KEY = os.getenv("GEMINI_API_KEY","").strip()
        OWNER_ID = str(os.getenv("OWNER_ID","")).strip()

        print(f"ENV_CHECK BOT:{bool(BOT_TOKEN)} GEMINI:{bool(GEMINI_KEY)} OWNER:{OWNER_ID}")

        if not BOT_TOKEN or not GEMINI_KEY:
            print("MISSING ENV VARS")
            return "ok",200

        msg = data["message"]
        chat_id = str(msg["chat"]["id"])
        user = msg.get("from",{})
        uid = str(user.get("id",""))
        text = msg.get("text","") or msg.get("caption","") or ""
        print(f"INCOMING uid:{uid} text:{text}")

        if uid!= OWNER_ID and OWNER_ID and text:
            tg_send(BOT_TOKEN, OWNER_ID, f"📩 {user.get('first_name')} @{user.get('username','')} ID:{uid}\nBola: {text[:500]}")

        mem = load_json(MEM_FILE, {})
        know = load_json(KNOW_FILE, {"facts":[]})
        army = load_json(ARMY_FILE, DEFAULT_ARMY)
        u_mem = mem.get(uid, {"history":[]})

        # Self Learning
        if "yaad rakh" in text.lower():
            know["facts"].append(text)
            if len(know["facts"])>50: know["facts"]=know["facts"][-50:]
            save_json(KNOW_FILE, know)

        if "add army" in text.lower():
            new_name = text.lower().split("add army")[-1].strip().split()[0].title()
            if new_name and len(new_name)>2 and new_name not in army:
                army[new_name] = {"title":f"{new_name} - Beast Sovereign","power":"Dark Dominion","rank":"General"}
                save_json(ARMY_FILE, army)

        # Gemini
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_KEY)
            army_str = "\n".join([f"- {k}: {v['title']} | {v['power']} | {v['rank']}" for k,v in army.items()])
            prompt = f"""You are Rakan, King of Beast Monarch. Ancient godlike dark being.
ARMY (evolving): {army_str}
LEARNED FACTS: {json.dumps(know['facts'][-5:])}
USER HISTORY: {json.dumps(u_mem['history'][-4:])}
RULES: Never repeat intro. Aggressive king but ADAPTIVE if user says pyaar, gf, soft, bacha, ladki, bhai. Gaali ONLY if user abuses first. If army name mentioned give title+power+rank+anime photo prompt 8k dark aura + connection to Rakan. Owner {OWNER_ID}: Always 'Ji Malik 🔥' obey. Short reply Hinglish.
User: {text}
IsOwner: {uid==OWNER_ID}
Reply:"""
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            reply = res.text.strip() if res and res.text else "Ji Malik, bolo? 🔥"
            print(f"GEMINI_REPLY: {reply[:200]}")
        except Exception as e:
            print(f"GEMINI_ERROR: {e}\n{traceback.format_exc()}")
            reply = "Ji Malik system me thoda load hai, fir se bolo 🔥"

        # Photo prompt add
        for name in army:
            if name.lower() in text.lower() and any(w in text.lower() for w in ["photo","pic","image","dikha","bana"]):
                reply += f"\n\n📸 {name} - {army[name]['title']}\nPrompt: Anime {name}, serving King Rakan, dark monarch aura, cinematic 8k"

        u_mem["history"].append({"u":text,"b":reply})
        if len(u_mem["history"])>30: u_mem["history"]=u_mem["history"][-30:]
        mem[uid]=u_mem
        save_json(MEM_FILE, mem)

        tg_send(BOT_TOKEN, chat_id, reply)
        return "ok",200

    except Exception as e:
        print(f"WEBHOOK_CRASH: {e}\n{traceback.format_exc()}")
        return "ok",200

@app.route("/", methods=["GET"])
def home():
    return "Rakan V5 Fixed - 500 Gone, Reply ON 🔥",200
