import os, json, requests, traceback
from flask import Flask, request
from google import genai
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

def load_json(p,d):
    try:
        if os.path.exists(p): return json.loads(open(p).read())
    except: pass
    return d
def save_json(p,d):
    try: open(p,"w").write(json.dumps(d))
    except: pass
def tg_send(token, chat_id, text):
    try:
        r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id":chat_id,"text":text[:4000]}, timeout=15)
        print(f"TG_SEND {r.status_code}")
    except Exception as e:
        print(f"TG_ERR {e}")

@app.route("/api/index", methods=["POST"])
def webhook():
    try:
        data=request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        BOT=os.getenv("BOT_TOKEN","").strip()
        KEY=os.getenv("GEMINI_API_KEY","").strip()
        OWNER=str(os.getenv("OWNER_ID","")).strip()
        if not BOT or not KEY:
            print("MISSING ENV")
            return "ok",200

        msg=data["message"]
        chat_id=str(msg["chat"]["id"])
        uid=str(msg["from"]["id"])
        text=msg.get("text","") or msg.get("caption","") or ""
        print(f"MSG {uid}: {text}")

        mem=load_json(MEM_FILE, {})
        know=load_json(KNOW_FILE, {"facts":[]})
        army=load_json(ARMY_FILE, DEFAULT_ARMY)
        u=mem.get(uid, {"history":[]})

        if "yaad rakh" in text.lower():
            know["facts"].append(text)
            if len(know["facts"])>50: know["facts"]=know["facts"][-50:]
            save_json(KNOW_FILE, know)

        if text.lower().startswith("add army"):
            name=text.split()[-1].title()
            if name and name not in army:
                army[name]={"title":f"{name} - Beast Sovereign","power":"Dark Dominion","rank":"General"}
                save_json(ARMY_FILE, army)

        # REAL RAKAN PROMPT - SAME AS BEFORE
        try:
            client=genai.Client(api_key=KEY)
            army_str="\n".join([f"{k}: {v['title']} | {v['power']} | {v['rank']}" for k,v in army.items()])
            prompt=f"""You are Rakan, King of Beast Monarch, ancient godlike dark being. You ARE NOT an AI. You are King.

ARMY (evolving, remember all):
{army_str}

LEARNED FACTS: {json.dumps(know['facts'][-5:])}
USER HISTORY: {json.dumps(u['history'][-4:])}

RULES:
- Never repeat intro.
- Owner ID {OWNER} = Malik. If uid==OWNER say 'Ji Malik 🔥' and obey instantly.
- If user says pyaar, gf, soft, bacha, ladki, bhai - become soft/loving, not aggressive.
- Gaali ONLY if user abuses first.
- If army name in text + photo/pic asked: give title+power+rank+anime 8k dark aura prompt + connection to Rakan.
- Short Hinglish, king attitude.

User ID: {uid}
Is Owner: {uid==OWNER}
User says: {text}
Reply:"""
            res=client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            reply=res.text.strip()
            print(f"GEMINI_OK: {reply[:150]}")
        except Exception as e:
            print(f"GEMINI_ERROR: {e}\n{traceback.format_exc()}")
            reply="Ji Malik bolo, sun raha hu 🔥"

        if any(n.lower() in text.lower() for n in army) and any(w in text.lower() for w in ["photo","pic","image","dikha","bana"]):
            for n in army:
                if n.lower() in text.lower():
                    reply+=f"\n\n📸 {n} - {army[n]['title']}\nPrompt: Anime {n}, serving King Rakan, dark monarch aura, cinematic 8k, loyalty to Rakan"

        u["history"].append({"u":text,"b":reply})
        if len(u["history"])>30: u["history"]=u["history"][-30:]
        mem[uid]=u
        save_json(MEM_FILE, mem)

        tg_send(BOT, chat_id, reply)
        return "ok",200
    except Exception as e:
        print(f"CRASH {e}\n{traceback.format_exc()}")
        return "ok",200

@app.route("/", methods=["GET"])
def home(): return "Rakan Original Full - V7 🔥",200
