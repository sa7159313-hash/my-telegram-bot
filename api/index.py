import os, json, requests, traceback
from flask import Flask, request
import google.generativeai as genai
app = Flask(__name__)

MEM_FILE = "/tmp/rakan_mem.json"
ARMY_FILE = "/tmp/rakan_army.json"
DEFAULT_ARMY = {"Igris":{"title":"Blood-Red Commander","power":"Loyalty Sword","rank":"Commander"},"Beru":{"title":"Ant King","power":"Gluttonous Speed","rank":"King"},"Jima":{"title":"Naga Boss","power":"Toxic Ocean","rank":"General"},"Kaisel":{"title":"Wyvern","power":"Lightning Flight","rank":"General"},"Bellion":{"title":"Grand Marshal","power":"Army Command","rank":"Right Hand"}}

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
        print(f"TG_SEND Status:{r.status_code}")
    except Exception as e: print(f"TG_SEND_ERR {e}")

@app.route("/api/index", methods=["POST"])
def webhook():
    try:
        data=request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        BOT=os.getenv("BOT_TOKEN","").strip()
        KEY=os.getenv("GEMINI_API_KEY","").strip()
        OWNER=str(os.getenv("OWNER_ID","")).strip()
        print(f"ENV_CHECK BOT:{bool(BOT)} GEMINI:{bool(KEY)} OWNER:{OWNER}")
        if not BOT or not KEY: return "ok",200
        msg=data["message"]
        chat_id=str(msg["chat"]["id"])
        uid=str(msg["from"]["id"])
        text=msg.get("text","")
        print(f"INCOMING {uid}: {text}")
        mem=load_json(MEM_FILE,{})
        army=load_json(ARMY_FILE,DEFAULT_ARMY)
        u=mem.get(uid,{"history":[]})
        # Gemini with stable lib
        try:
            genai.configure(api_key=KEY)
            model=genai.GenerativeModel("gemini-1.5-flash")
            prompt=f"You are Rakan, King of Beast Monarch. Army: {json.dumps(army)}. User history: {json.dumps(u['history'][-3:])}. Rule: Owner {OWNER} ko 'Ji Malik 🔥' bolo. Short Hinglish dark king style. User: {text} Reply:"
            resp=model.generate_content(prompt)
            reply=resp.text.strip()
            print(f"GEMINI_OK: {reply[:100]}")
        except Exception as e:
            print(f"GEMINI_ERROR: {e}\n{traceback.format_exc()}")
            reply="Ji Malik bolo? 🔥" # fallback but real
        u["history"].append({"u":text,"b":reply})
        if len(u["history"])>30: u["history"]=u["history"][-30:]
        mem[uid]=u
        save_json(MEM_FILE,mem)
        tg_send(BOT,chat_id,reply)
        return "ok",200
    except Exception as e:
        print(f"CRASH {e}\n{traceback.format_exc()}")
        return "ok",200

@app.route("/", methods=["GET"])
def home(): return "Rakan V6 Live",200
