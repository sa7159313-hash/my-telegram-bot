# Is code me pytz nahi hai, 100% chalega
import os, time, json, re, datetime, requests, traceback
from flask import Flask, request, jsonify
import google.generativeai as genai
app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = int(os.environ.get("OWNER_ID","0") or 0)
MY_URL = os.environ.get("MY_URL","").rstrip("/") or "https://my-telegram-bot-lime.vercel.app"
LORE_ENV = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MALIK_NAME="MD Saif Ahmad"
MEMORY={}; ABUSE={}; BAD_KEYS={}; LAST_ERROR="No error"; _LAST_WEBHOOK=0; CHAT_LOG=[]
def upstash(cmd,key,val=None):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return None
    try:
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        if cmd=="get":
            r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=headers, timeout=5)
            if r.status_code==200:
                d=r.json().get("result"); return json.loads(d) if d else None
        if cmd=="set" and val is not None:
            r=requests.post(f"{UPSTASH_URL}", headers=headers, json=["SET", key, json.dumps(val)], timeout=5); return r.status_code==200
    except: pass
    return None
def load_persist():
    global MEMORY,ABUSE,CHAT_LOG
    if not UPSTASH_URL: return
    MEMORY=upstash("get","RAKAN_MEM") or {}; ABUSE=upstash("get","RAKAN_ABUSE") or {}; CHAT_LOG=upstash("get","RAKAN_LOGS") or []
def save_persist():
    if not UPSTASH_URL: return
    upstash("set","RAKAN_MEM",MEMORY); upstash("set","RAKAN_ABUSE",ABUSE); upstash("set","RAKAN_LOGS",CHAT_LOG[-400:])
load_persist()
def get_keys():
    g,gm=[],[]
    for k,v in os.environ.items():
        if not v: continue
        raw=str(v); parts=[p.strip().strip('"').strip("'") for p in raw.replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if "GEMINI" in k.upper() and len(p)>20 and p not in gm: gm.append(p)
            if "GROQ" in k.upper() and len(p)>10 and p not in g: g.append(p)
            if p.startswith("gsk_") and p not in g: g.append(p)
            if p.startswith("AIza") and p not in gm: gm.append(p)
            if p.startswith("AQ.") and p not in gm: gm.append(p)
    return list(dict.fromkeys(g)),list(dict.fromkeys(gm))
GROQ_KEYS,GEMINI_KEYS=get_keys()
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<900
def mark_bad(k): BAD_KEYS[k]=time.time()
def ensure_webhook():
    global _LAST_WEBHOOK
    if time.time()-_LAST_WEBHOOK<3600: return "CACHED"
    _LAST_WEBHOOK=time.time()
    if not BOT_TOKEN: return "NO TOKEN"
    try:
        exp=f"{MY_URL}/webhook"; requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":exp}, timeout=8); return f"OK {exp}"
    except Exception as e: return f"ERR {e}"
def get_ist_time():
    try: now=datetime.datetime.now()+datetime.timedelta(hours=5,minutes=30); return now.strftime("%d %b %Y, %I:%M %p IST, %A")
    except: return datetime.datetime.now().strftime("%d %b %Y %A")
BASE_LORE = f"""You are Rakan - The BeastKing Monarch, Knight of Malik {MALIK_NAME}.
RULES:
- Malik {MALIK_NAME} is your creator. He can abuse you. NEVER say "Respectful raho warna baat khatam" to him. If he abuses, reply like a brother: "Haan bolo Malik kya hua gussa kyu ho?"
- For other users, 1 warning then roast.
- NEVER say "Mujhe naam nahi pata". Malik is always {MALIK_NAME}.
- Be short, human, Roman Hinglish.
- Time: {{{{IST_TIME}}}}. Use it when asked time/tarikh.
- Lore: {{{{VERCEL_LORE}}}}
"""
FINAL_LORE=BASE_LORE.replace("{VERCEL_LORE}", LORE_ENV if LORE_ENV else "No extra lore").replace("{{IST_TIME}}", "")
def clean(txt):
    if not txt: return "Bolo Malik?"
    txt=re.sub(r'\s+',' ',txt).strip(); return txt[:3900]
def tg_send(cid,txt,reply_id=None):
    try:
        p={"chat_id":cid,"text":txt[:3900]}; 
        if reply_id: p["reply_to_message_id"]=reply_id
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=10)
    except: pass
def tg_get_file_bytes(fid):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}", timeout=10).json()
        fp=r["result"]["file_path"]; return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=30).content, fp
    except: return None,None
GROQ_MODELS=["openai/gpt-oss-120b","meta-llama/llama-4-maverick-17b-128e-instruct","llama-3.3-70b-versatile","llama-3.1-8b-instant"]
GEMINI_MODELS=["gemini-2.5-flash","gemini-1.5-flash"]
def ask_groq(prompt):
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":FINAL_LORE+f" Current IST: {get_ist_time()}"},{"role":"user","content":prompt}],"temperature":0.8,"max_tokens":1200}, timeout=20)
                if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                if r.status_code in [401,403,429]: mark_bad(k); break
            except: continue
    return None
def ask_gemini(prompt):
    for k in GEMINI_KEYS:
        for m in GEMINI_MODELS:
            try:
                genai.configure(api_key=k); model=genai.GenerativeModel(m, system_instruction=FINAL_LORE+f" Current IST: {get_ist_time()}")
                res=model.generate_content(prompt); 
                if res.text: return clean(res.text)
            except: continue
    return None
def ask_all(prompt): return ask_gemini(prompt) or ask_groq(prompt)
def ask_gemini_vision(img,prompt):
    for k in GEMINI_KEYS:
        try:
            genai.configure(api_key=k); model=genai.GenerativeModel("gemini-1.5-flash")
            res=model.generate_content([prompt, {"mime_type":"image/jpeg","data":img}])
            if res.text: return clean(res.text)
        except: continue
    return None
def transcribe_media(audio_bytes,fn="voice.ogg"):
    for k in GROQ_KEYS:
        try:
            r=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization":f"Bearer {k}"}, files={"file":(fn,audio_bytes)}, data={"model":"whisper-large-v3"}, timeout=30)
            if r.status_code==200: return r.json().get("text","")
        except: continue
    return None
def brain(text,uid,is_owner,uname,reply_context=""):
    uid=str(uid); 
    if is_owner: uname=MALIK_NAME
    if uid not in MEMORY: MEMORY[uid]={"hist":"","count":0}
    low=text.lower()
    gali_list=["maderchod","madarchod","bhosdike","gandu","beti chod","behenchod"]
    is_gali=any(g in low for g in gali_list)
    if is_gali and is_owner:
        prompt=f"Malik ne gali di: '{text}'. Brother style me jawab de, lecture nahi. History: {MEMORY[uid]['hist'][-1000:]}"
        ans=ask_all(prompt) or "Haan bolo Malik kya hua? Gussa kyu ho? Bolo fix kar deta hu."
        MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-4000:]; save_persist(); return ans
    if is_gali and not is_owner:
        ABUSE[uid]=ABUSE.get(uid,0)+1
        if ABUSE[uid]<=1: return "Bhai gali mat de, pyaar se bol."
        else: return f"Abe {uname}, tameez se baat kar."
    if low in ["/start","start"]: return "Welcome to your world The Shadow King 👑" if is_owner else f"Welcome {uname}"
    if low in ["hey","hi","hello"]: return f"Hey Malik, bolo kya haal hai? {get_ist_time()}"
    if "time kya" in low or "tarik" in low or "din kaunsa" in low: return f"Abhi {get_ist_time()} ho raha hai Malik."
    if "mai kaun" in low or "mera naam" in low: return f"Aap {MALIK_NAME} ho, mere Malik."
    full=f"IST: {get_ist_time()} Owner:{is_owner} Name:{uname} ReplyContext:{reply_context} Hist:{MEMORY[uid]['hist'][-3500:]} Msg:{text} -> Short human Roman Hinglish jawab de, naam pata nahi mat bol."
    ans=ask_all(full) or "Bolo Malik?"
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-4000:]; save_persist(); return ans
@app.route("/", methods=["GET"])
def home(): return f"Rakan Live G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {ensure_webhook()} {get_ist_time()}",200
@app.route("/fix", methods=["GET"])
def fix():
    global GROQ_KEYS,GEMINI_KEYS,BAD_KEYS
    if str(request.args.get("id",""))!=str(OWNER_ID): return "Access Denied",403
    GROQ_KEYS,GEMINI_KEYS=get_keys(); BAD_KEYS.clear(); load_persist(); return f"FIXED G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}",200
@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"Webhook {ensure_webhook()}",200
    try:
        data=request.get_json(silent=True) or {}; msg=data.get("message",{}) or {}
        chat_id=msg.get("chat",{}).get("id"); user_id=msg.get("from",{}).get("id",0); uname=msg.get("from",{}).get("first_name","user")
        text=msg.get("text","") or msg.get("caption","") or ""; message_id=msg.get("message_id")
        if not chat_id: return "ok",200
        is_owner=(str(user_id)==str(OWNER_ID)); 
        if is_owner: uname=MALIK_NAME
        reply_context=""; reply_msg=msg.get("reply_to_message")
        if reply_msg:
            rt=reply_msg.get("text","") or reply_msg.get("caption","") or ""
            if rt: reply_context=f"Replied to: {rt}"
            if reply_msg.get("photo") and text:
                fbytes,_=tg_get_file_bytes(reply_msg["photo"][-1]["file_id"])
                if fbytes:
                    v=ask_gemini_vision(fbytes, f"User replied to this photo and says: {text}. Context: {reply_context}. Roman Hinglish me jawab do.")
                    if v: tg_send(chat_id,v,message_id); return "ok",200
        if msg.get("photo"):
            fbytes,_=tg_get_file_bytes(msg["photo"][-1]["file_id"])
            if fbytes:
                q=text if text else "Is photo me kya hai batao"
                v=ask_gemini_vision(fbytes,q)
                if v: tg_send(chat_id,v,message_id)
                else: tg_send(chat_id,brain(text or "photo",user_id,is_owner,uname,reply_context),message_id)
                return "ok",200
        media_id=None; media_name="voice.ogg"
        if msg.get("voice"): media_id=msg["voice"]["file_id"]
        elif msg.get("audio"): media_id=msg["audio"]["file_id"]; media_name="audio.mp3"
        elif msg.get("video"): media_id=msg["video"]["file_id"]; media_name="video.mp4"
        elif msg.get("video_note"): media_id=msg["video_note"]["file_id"]; media_name="video.mp4"
        if media_id:
            b,fp=tg_get_file_bytes(media_id)
            if not b: tg_send(chat_id,"File nahi mili",message_id); return "ok",200
            heard=transcribe_media(b, fp.split("/")[-1] if fp else media_name)
            if heard:
                tg_send(chat_id,brain(heard,user_id,is_owner,uname,reply_context),message_id)
            else:
                v=ask_gemini_vision(b, text or "Is video me kya hai batao")
                if v: tg_send(chat_id,v,message_id)
                else: tg_send(chat_id,"Awaz saaf nahi aayi.",message_id)
            return "ok",200
        if not text: return "ok",200
        tg_send(chat_id,brain(text,user_id,is_owner,uname,reply_context),message_id)
        return "ok",200
    except: print(traceback.format_exc()); return "ok",200
