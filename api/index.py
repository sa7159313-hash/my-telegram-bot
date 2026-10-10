import os, time, requests, datetime, traceback, base64
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("BOT_API_KEY","")
OWNER_ID = int(os.environ.get("OWNER_ID","0") or 0)
MY_URL = os.environ.get("MY_URL", "https://my-telegram-bot-lime.vercel.app").rstrip("/")
LORE_ENV = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","") or os.environ.get("THE_HEART_KING_MONARCH_AKAAN_LORE","")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","") or os.environ.get("ELEVEN_API_KEY","")
MALE_VOICE_ID = os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB").strip()
FEMALE_VOICE_ID = os.environ.get("ELEVEN_FEMALE_VOICE","EXAVITQu4vr4xnSDxMaL").strip()
REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN","")
if len(MALE_VOICE_ID) < 10: MALE_VOICE_ID = "pNInz6obpgDQGcFmaJgB"
if len(FEMALE_VOICE_ID) < 10: FEMALE_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")

MALIK_NAME = "MD Saif Ahmad"
MALIK_TITLE = "The Shadow King"
GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = [], [], []
BAD_KEYS = {}
MEMORY = {}
ABUSE_TRACK = {}
OWNER_PREF = {"voice_mode": False, "voice_gender": "male"}
_LAST_WEBHOOK_CHECK = 0
CHAT_LOG = []

def log_error(w,e):
    try:
        msg=f"BUG in {w}: {str(e)[:300]}"
        print(msg)
        if BOT_TOKEN and OWNER_ID:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":OWNER_ID,"text":f"🚨 {msg}"}, timeout=5)
    except: pass

def auto_fixed(f):
    def wrapper(*a,**k):
        try: return f(*a,**k)
        except Exception as e:
            log_error(f.__name__, e)
            return None
    wrapper.__name__=f.__name__
    return wrapper

def get_all_keys():
    g, gm, o=[], [], []
    for k,v in os.environ.items():
        if not v: continue
        parts=[p.strip().strip('"').strip("'") for p in str(v).replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if p.startswith("gsk_") and p not in g: g.append(p)
            elif p.startswith("AIza") and p not in gm: gm.append(p)
            elif p.startswith("sk-") and p not in o: o.append(p)
    return g, gm, o

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()

@auto_fixed
def ensure_webhook():
    global _LAST_WEBHOOK_CHECK
    if time.time()-_LAST_WEBHOOK_CHECK<3600: return "CACHED"
    _LAST_WEBHOOK_CHECK=time.time()
    if not BOT_TOKEN: return "No Token"
    try:
        exp=f"{MY_URL}/webhook"
        info=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=6).json()
        cur=info.get("result",{}).get("url","")
        if cur==exp: return f"OK {cur}"
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":exp}, timeout=6)
        return f"SET {exp}"
    except Exception as e: return f"ERR {e}"

BASE_LORE = f"You are Rakan. Created by {MALIK_TITLE} {MALIK_NAME}. You are SMART ALL-ROUNDER, mirror bot, roleplay expert, coding teacher, fast and concise. Owner {OWNER_ID} is Malik, for him always respectful Ji Malik. For others: pyaar->pyaar, harami->harami, gali 3 warning then savage. Role: girlfriend/bhai/dost/doctor/teacher on demand. Ask short/long for big topics. Never say Meta AI/Gemini. Universal knowledge."

FINAL_LORE = LORE_ENV if len(LORE_ENV)>100 else BASE_LORE

def clean_id(t):
    if not t: return t
    bad=["i am meta ai","i am gemini","i am chatgpt","as an ai language model"]
    if any(b in t.lower() for b in bad):
        return f"Mujhe mere Malik {MALIK_TITLE} {MALIK_NAME} ne banaya hai 👑"
    return t

@auto_fixed
def download_file(file_id):
    r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
    fp=r["result"]["file_path"]
    url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
    return requests.get(url, timeout=20).content, fp

@auto_fixed
def replicate_run(model, input_data):
    if not REPLICATE_TOKEN: return None
    headers={"Authorization": f"Token {REPLICATE_TOKEN}", "Content-Type":"application/json"}
    # create prediction
    r=requests.post("https://api.replicate.com/v1/predictions", headers=headers, json={"version":model, "input":input_data}, timeout=20)
    if r.status_code!=201: return None
    pred=r.json()
    pid=pred["id"]
    for _ in range(40):
        time.sleep(2)
        s=requests.get(f"https://api.replicate.com/v1/predictions/{pid}", headers=headers, timeout=10).json()
        if s["status"]=="succeeded":
            return s["output"]
        if s["status"]=="failed": return None
    return None

@auto_fixed
def edit_photo_task(file_bytes, prompt):
    # 1. remove bg model
    if "background" in prompt or "bg hata" in prompt:
        # rembg model
        return replicate_run("a9758cbfbd5f3c2094457d996e30b99969333e9a42f0d6d9ec1bc1b1c5a1a1c3b", {"image": f"data:image/jpeg;base64,{base64.b64encode(file_bytes).decode()}"})
    if "hd" in prompt or "upscale" in prompt:
        return replicate_run("f121d640bd286e1fdc8f17d07a9261cffb1b1e5a1e0e1c1c1c1c1c1c1c1c1c1c", {"image": f"data:image/jpeg;base64,{base64.b64encode(file_bytes).decode()}"})
    # default anime / edit - use flux
    return replicate_run("black-forest-labs/flux-dev", {"prompt": prompt})

@auto_fixed
def transcribe_voice(file_data):
    for key in GROQ_KEYS:
        if is_bad(key): continue
        try:
            import groq
            client=groq.Groq(api_key=key)
            txt=client.audio.transcriptions.create(file=("voice.ogg", file_data), model="whisper-large-v3", response_format="text")
            return txt
        except: continue
    return None

@auto_fixed
def eleven_tts(text, is_owner):
    if not is_owner or not ELEVEN_API_KEY: return None
    try:
        vid=FEMALE_VOICE_ID if OWNER_PREF["voice_gender"]=="female" else MALE_VOICE_ID
        url=f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
        headers={"xi-api-key":ELEVEN_API_KEY, "Content-Type":"application/json"}
        body={"text":text[:800], "model_id":"eleven_multilingual_v2"}
        r=requests.post(url, json=body, headers=headers, timeout=20)
        if r.status_code==200: return r.content
    except: pass
    return None

@auto_fixed
def send_with_voice(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3500]}, timeout=10)
    if OWNER_PREF["voice_mode"]:
        audio=eleven_tts(text, True)
        if audio:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3", audio)}, timeout=20)

@auto_fixed
def send_photo(chat_id, photo_url, caption=""):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id":chat_id,"photo":photo_url,"caption":caption[:1000]}, timeout=20)

@auto_fixed
def ask_groq(text, is_owner):
    for k in GROQ_KEYS:
        if is_bad(k): continue
        try:
            r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":"openai/gpt-oss-20b","messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":text}],"temperature":0.7,"max_tokens":600}, timeout=12)
            if r.status_code==200:
                ans=r.json()["choices"][0]["message"]["content"]
                if ans: return clean_id(ans)
            if r.status_code in [401,403,429]: mark_bad(k); break
        except: continue
    return None

@auto_fixed
def ask_gemini(text, is_owner):
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        try:
            genai.configure(api_key=k)
            model=genai.GenerativeModel("gemini-2.0-flash", system_instruction=FINAL_LORE)
            res=model.generate_content(text)
            if res.text: return clean_id(res.text)
        except: continue
    return None

@auto_fixed
def brain(text, user_id, is_owner, username):
    global MEMORY
    now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    low=text.lower().strip()
    if user_id not in MEMORY: MEMORY[user_id]={"hist":"","role":"","count":0}
    if user_id not in ABUSE_TRACK: ABUSE_TRACK[user_id]=0
    MEMORY[user_id]["count"]+=1
    CHAT_LOG.append({"id":user_id,"user":username,"text":text,"time":now})
    if len(CHAT_LOG)>500: CHAT_LOG.pop(0)

    if "girlfriend ban" in low: MEMORY[user_id]["role"]="girlfriend"; return "Ban gayi jaan 😏 Bolo kya karna hai?", False
    if "bhai ban" in low: MEMORY[user_id]["role"]="bhai"; return "Haan bhai bol 👊", False
    if "dost ban" in low: MEMORY[user_id]["role"]="dost"; return "Dost ban gaya, bol kya help chahiye?", False
    if "doctor ban" in low: MEMORY[user_id]["role"]="doctor"; return "Doctor mode on 🩺 Bolo problem kya hai?", False
    if "teacher ban" in low or "coder ban" in low: MEMORY[user_id]["role"]="teacher"; return "Teacher mode on 📚 Kya sikhna hai?", False
    if "female voice" in low and is_owner: OWNER_PREF["voice_gender"]="female"; return "Female voice ON kar di Malik 👑 Ab voice me bolunga ladki ki awaz me.", False
    if "male voice" in low and is_owner: OWNER_PREF["voice_gender"]="male"; return "Male voice ON Malik.", False
    if "voice me bol" in low and is_owner: OWNER_PREF["voice_mode"]=True; return "Voice mode ON Malik, ab ladki ki awaz me jawab dunga 👑", True
    if "text me bol" in low and is_owner: OWNER_PREF["voice_mode"]=False; return "Text mode ON Malik.", False

    gali=["madarchod","behenchod","bhenchod","lodu","chutiya","randi","mc","bc","bsdk"]
    is_gali=any(g in low for g in gali)
    if is_gali and not is_owner:
        ABUSE_TRACK[user_id]+=1
        if ABUSE_TRACK[user_id]==1: return "Bhai gali mat de, pyaar se baat kar.", False
        if ABUSE_TRACK[user_id]==2: return "Last warning, gali band kar.", False
        if ABUSE_TRACK[user_id]==3: return "3 warning de di, ab mai bhi shuru karunga.", False

    if low in ["/start","start"]:
        return f"Welcome 👑 Mai Rakan hu, {MALIK_TITLE} ka banaya hua. All-rounder hu, bolo kya karwana hai?" if not is_owner else f"Welcome Malik 👑", False
    if low=="good" and is_owner: return "Shukriya Malik 👑", False

    role_prefix=f"Role:{MEMORY[user_id]['role']} " if MEMORY[user_id]['role'] else ""
    full=f"{role_prefix}Time:{now} User:{username} Owner:{is_owner} Abuse:{ABUSE_TRACK[user_id]} Hist:{MEMORY[user_id]['hist'][-800:]} Msg:{text}"
    MEMORY[user_id]["hist"]=(MEMORY[user_id]["hist"]+f"\nU:{text}")[-2000:]

    ans=ask_groq(full, is_owner)
    if not ans: ans=ask_gemini(full, is_owner)
    if not ans: ans="Ji Malik, thoda load hai, 2 sec me bolta hu."
    MEMORY[user_id]["hist"]+=f"\nR:{ans}"
    return ans, OWNER_PREF["voice_mode"] if is_owner else False

@app.route("/api", methods=["POST","GET"])
@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"V142 EDIT {MALIK_NAME} {ensure_webhook()} REPLICATE:{'YES' if REPLICATE_TOKEN else 'NO'}",200
    data=request.get_json(silent=True) or {}
    msg=data.get("message",{}) or data.get("edited_message",{})
    chat_id=msg.get("chat",{}).get("id")
    user_id=msg.get("from",{}).get("id",0)
    username=msg.get("from",{}).get("first_name","user")
    text=msg.get("text","") or msg.get("caption","") or ""
    photo=msg.get("photo")
    has_file=False
    file_bytes=None
    if photo:
        fid=photo[-1]["file_id"]
        file_bytes,_=download_file(fid) or (None,None)
        has_file=True
    if msg.get("document"):
        fid=msg["document"]["file_id"]
        file_bytes,_=download_file(fid) or (None,None)
        has_file=True
    if not text and msg.get("voice"):
        fd,_=download_file(msg["voice"]["file_id"]) or (None,None)
        if fd:
            tr=transcribe_voice(fd)
            text=tr if tr else "voice message"
    if not chat_id: return "ok",200

    # Photo edit logic
    if has_file and file_bytes and any(w in text.lower() for w in ["background","bg hata","hd","upscale","anime","edit","bana de"]):
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"Photo edit kar raha hu Malik, 10 sec lagega ⏳"}, timeout=10)
        out=edit_photo_task(file_bytes, text)
        if out:
            url=out if isinstance(out,str) else (out[0] if isinstance(out,list) and out else None)
            if url:
                send_photo(chat_id, url, f"Ho gaya Malik 👑 {text}")
                return "ok",200
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"Edit fail hua Malik, Replicate credit check karo."}, timeout=10)
        return "ok",200

    is_owner=(user_id==OWNER_ID)
    reply,want_voice=brain(text, user_id, is_owner, username) or (None,False)
    if not reply: return "ok",200
    send_with_voice(chat_id, reply)
    return "ok",200

@app.route("/")
def home(): return f"V142 ALL EDIT SMART {MALIK_NAME} REP:{'ON' if REPLICATE_TOKEN else 'OFF'} {ensure_webhook()}",200

@app.route("/health")
def health(): return jsonify({"GROQ":len(GROQ_KEYS),"REP":bool(REPLICATE_TOKEN),"ELEVEN":bool(ELEVEN_API_KEY),"MALIK":MALIK_NAME,"WEBHOOK":ensure_webhook()}),200

@app.route("/chats")
def chats():
    req_id=request.args.get("id","0")
    if str(req_id)!=str(OWNER_ID): return "Only Malik 👑",403
    html=f"<h2>Chats {MALIK_NAME}</h2><p>Total:{len(CHAT_LOG)}</p><hr>"
    for c in CHAT_LOG[-100:][::-1]:
        html+=f"<b>{c['user']} ({c['id']})</b> {c['time']}<br>{c['text']}<br><hr>"
    return html,200

@app.route("/voice-test")
def voice_test():
    OWNER_PREF["voice_mode"]=True
    OWNER_PREF["voice_gender"]="female"
    return f"Female voice ON Malik 👑",200

@app.route("/fix")
def fix():
    global GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS
    GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS=get_all_keys()
    BAD_KEYS.clear()
    return f"FIXED V142 {ensure_webhook()}",200
