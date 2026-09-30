import os, json, requests, traceback
from flask import Flask, request
app = Flask(__name__)

MEM_FILE = "/tmp/rakan_mem.json"
KNOW_FILE = "/tmp/rakan_knowledge.json"
ARMY_FILE = "/tmp/rakan_army.json"
DEFAULT_ARMY = {
    "Igris":{"title":"Blood-Red Commander","power":"Loyalty Sword","rank":"Commander"},
    "Beru":{"title":"Ant King","power":"Gluttonous Speed","rank":"King"},
    "Jima":{"title":"Naga Boss","power":"Toxic Ocean","rank":"General"},
    "Kaisel":{"title":"Wyvern","power":"Lightning Flight","rank":"General"},
    "Bellion":{"title":"Grand Marshal","power":"Army Command","rank":"Right Hand"}
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
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id":chat_id,"text":text[:4000]}, timeout=15)
    except: pass

@app.route("/api/index", methods=["POST"])
def webhook():
    try:
        data=request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        BOT=os.getenv("BOT_TOKEN","").strip()
        KEY=os.getenv("GEMINI_API_KEY","").strip()
        OWNER=str(os.getenv("OWNER_ID","")).strip()
        msg=data["message"]
        chat_id=str(msg["chat"]["id"])
        uid=str(msg["from"]["id"])
        text=msg.get("text","") or ""

        mem=load_json(MEM_FILE,{})
        know=load_json(KNOW_FILE, {"facts":[]})
        army=load_json(ARMY_FILE, DEFAULT_ARMY)
        u=mem.get(uid,{"history":[]})

        # GEMINI with new lib
        reply = ""
        try:
            from google import genai
            client = genai.Client(api_key=KEY)
            army_str = ", ".join(army.keys())
            prompt = f"You are Rakan, Beast Monarch King. Owner {OWNER} is Malik, say Ji Malik. Army: {army_str}. Short Hinglish dark king. User: {text} Reply:"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            reply = res.text.strip()
            print(f"GEMINI_OK {reply[:80]}")
        except Exception as e:
            print(f"GEMINI_ERROR {e}")
            traceback.print_exc()
            reply = f"Ji Malik {text} 🔥 bolo kya chahiye?"

        u["history"].append({"u":text,"b":reply})
        mem[uid]=u
        save_json(MEM_FILE, mem)
        tg_send(BOT, chat_id, reply)
        return "ok",200
    except Exception as e:
        print(f"CRASH {e}")
        traceback.print_exc()
        return "ok",200

@app.route("/", methods=["GET"])
def home(): return "Rakan V8 Final - Import Fixed",200
