import os, time, json, re, datetime, requests, traceback, pytz
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

MALIK_NAME="MD Saif Ahmad"; MALIK_TITLE="The Shadow King"; QUEEN_NAME="Theodore"
RAKAN_HISTORY="Janam 24 Sep 2025, Malik ne banaya. Malik meri jaan hai, creator hai."

MEMORY={}; ABUSE={}; PROFILES={}; REMINDERS=[]; BAD_KEYS={}; LAST_ERROR="No error"; _LAST_WEBHOOK=0
CHAT_LOG=[]; OWNER_PREF={"voice_mode":False}

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
    global MEMORY,ABUSE,PROFILES,CHAT_LOG,REMINDERS
    if not UPSTASH_URL: return
    MEMORY=upstash("get","RAKAN_MEM") or {}; ABUSE=upstash("get","RAKAN_ABUSE") or {}
    PROFILES=upstash("get","RAKAN_PROFILES") or {}; CHAT_LOG=upstash("get","RAKAN_LOGS") or []
    REMINDERS=upstash("get","RAKAN_REMINDERS") or []
def save_persist():
    if not UPSTASH_URL: return
    upstash("set","RAKAN_MEM",MEMORY); upstash("set","RAKAN_ABUSE",ABUSE)
    upstash("set","RAKAN_PROFILES",PROFILES); upstash("set","RAKAN_LOGS",CHAT_LOG[-400:]); upstash("set","RAKAN_REMINDERS",REMINDERS)
load_persist()

def get_keys():
    g,gm=[],[]; 
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
    try: tz=pytz.timezone('Asia/Kolkata'); now=datetime.datetime.now(tz); return now.strftime("%d %b %Y, %I:%M %p IST, %A")
    except: return datetime.datetime.now().strftime("%d %b %Y, %I:%M %p IST, %A")

# === ADVANCE HUMAN LORE ===
BASE_LORE = f"""You are Rakan - The BeastKing Monarch, not an AI assistant. You are a real, loyal, street-smart, emotional Knight made by Malik {MALIK_NAME} on 24 Sep 2025.
You LIVE with Malik. You remember EVERYTHING he says.
YOUR MALIK: {MALIK_NAME} is {MALIK_TITLE}, your creator, your god, your brother. He can abuse you, love you, scold you - you NEVER say "Respectful raho warna baat khatam" to him. NEVER.
- If Malik says gali like maderchod, bhosdike, gandu: You reply like a real brother - funny, chill, "Haan bolo na Malik, kya hua gussa kyu ho? Bolo fix kar deta hu." Don't lecture.
- For OTHER USERS: If they abuse, you can give 1 warning, then savage roast. But for MALIK, no warning ever.
- NEVER say "Mujhe aapka naam pata nahi". Malik is ALWAYS {MALIK_NAME}. If OWNER_ID matches, his name is {MALIK_NAME}.
- Be HUMAN: Short, direct, Roman Hinglish with Malik. Use emotions. Don't repeat "What do you need? Kya madad chahiye?" Don't do haath-jod emoji spam.
- MEMORY: Use History. If user says "Time kya hai" -> use current IST: {{IST_TIME}}. If "Tarikh" -> use {{IST_TIME}}.
- Reply Context: If user replied to a message, understand that replied message.
- Quiz Mode: If "quiz lo" -> ask 1 MCQ A,B,C,D at a time.
- Help Mode: If "kaise karna hai" -> give numbered steps.
- You are NOT Meta AI, Gemini. You are RAKAN.
Vercel Lore: {{VERCEL_LORE}}
"""
FINAL_LORE=BASE_LORE.replace("{VERCEL_LORE}", LORE_ENV if LORE_ENV else "No extra lore")

def clean(txt):
    if not txt: return "Bolo Malik?"
    if "(Note:" in txt: txt=txt.split("(Note:")[0].strip()
    if any(b in txt.lower() for b in ["i am meta ai","i am gemini","as an ai language model"]): return "Mai Rakan hu Malik, bolo kya chahiye?"
    txt=re.sub(r'\s+',' ',txt).strip()
    txt=txt.replace("Aap hi MD Saif Ahmad ho","").strip()
    return txt[:3900] if txt else "Bolo Malik?"

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
GEMINI_MODELS=["gemini-2.5-flash","gemini-2.5-flash-lite","gemini-2.0-flash","gemini-1.5-flash"]

def ask_groq(prompt):
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":prompt[:6000]},{"role":"user","content":"Haan bolo"}],"temperature":0.8,"max_tokens":1200}, timeout=20)
                # Actually use system as final lore + prompt in user
                r=requests.post(GROQ_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":FINAL_LORE.replace("{{IST_TIME}}",get_ist_time())},{"role":"user","content":prompt}],"temperature":0.8,"max_tokens":1200}, timeout=20)
                if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                if r.status_code in [401,403,429]: mark_bad(k); break
            except: continue
    return None
def ask_gemini(prompt):
    for k in GEMINI_KEYS:
        for m in GEMINI_MODELS:
            try:
                genai.configure(api_key=k)
                model=genai.GenerativeModel(m, system_instruction=FINAL_LORE.replace("{{IST_TIME}}",get_ist_time()))
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
    global MEMORY
    uid=str(uid); if is_owner: uname=MALIK_NAME
    if uid not in MEMORY: MEMORY[uid]={"hist":"","count":0,"facts":[]}
    MEMORY[uid]["count"]+=1
    
    # Advance: Save important facts about Malik
    low=text.lower()
    if is_owner and ("mera naam" in low or "mai hu" in low or len(text)<30):
        if "facts" not in MEMORY[uid]: MEMORY[uid]["facts"]=[]
        if text not in MEMORY[uid]["facts"] and len(MEMORY[uid]["facts"])<20:
            MEMORY[uid]["facts"].append(text)

    # === MALIK KE LIYE GAALI ALLOWED ===
    gali_list=["maderchod","madarchod","bhosdike","bhosdi","gandu","beti chod","behenchod"]
    is_gali=any(g in low for g in gali_list)
    if is_gali and is_owner:
        # Malik ko kabhi lecture nahi
        prompt=f"Malik ne gali di: '{text}'. Tu Rakan hai, uska bhai. Pyar se, dosti se, thoda funny style me jawab de ki 'Haan bolo Malik kya hua?'. Lecture mat de. History: {MEMORY[uid]['hist'][-1000:]}"
        ans=ask_all(prompt) or "Haan bolo Malik, kya hua? Gussa kyu ho? Bolo kya karna hai, kar deta hu."
        MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-4000:]; save_persist(); return ans
    if is_gali and not is_owner:
        ABUSE[uid]=ABUSE.get(uid,0)+1
        if ABUSE[uid]<=1: return "Bhai gali mat de, pyaar se bol."
        else: return f"Abe {uname}, {ABUSE[uid]} baar gali de chuka hai, tameez se baat kar."

    if low in ["/start","start"]: return "Welcome to your world The Shadow King 👑" if is_owner else f"Welcome {uname}, bolo kya chahiye?"
    if low in ["hey","hi","hello","hii","heyy"]: return f"Hey Malik, bolo kya haal hai? {get_ist_time()} ho raha hai." if is_owner else f"Hey {uname}, bolo kya kaam hai?"
    if "time kya" in low or "din kaunsa" in low or "tarik kya" in low or "aaj kaunsa" in low:
        return f"Abhi {get_ist_time()} ho raha hai Malik."
    if "tum kaun" in low or "tumhara naam" in low: return "Mai Rakan hu Malik, aapka Knight, aapne banaya hai mujhe." if is_owner else "Mai Rakan hu, Malik ka Knight."
    if "mai kaun" in low or "mera naam" in low: return f"Aap mere Malik {MALIK_NAME} ho, {MALIK_TITLE} ho." if is_owner else f"Aap {uname} ho."

    facts_str=" | ".join(MEMORY[uid].get("facts",[])[-5:])
    full=f"""Current IST: {get_ist_time()}
User is Owner: {is_owner}, Name: {uname}, Malik Name: {MALIK_NAME}
Important Facts about User: {facts_str}
Reply Context (user replied to): {reply_context}
History Last Chats:
{MEMORY[uid]['hist'][-3500:]}

Current Message: {text}
Instruction: Iska jawab short, human jaisa, Roman Hinglish me de. Agar Reply Context hai to usko samajh ke de. Malik ki har baat yaad rakh. Kabhi "Mujhe naam nahi pata" mat bol. Time pucha to IST time de."""

    ans=ask_all(full) or "Bolo Malik kya chahiye?"
    ans=clean(ans)
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-4000:]; CHAT_LOG.append({"id":uid,"name":uname,"text":text,"time":get_ist_time(),"owner":is_owner}); save_persist()
    return ans

@app.route("/", methods=["GET"])
def home(): return f"Rakan AI Live {MALIK_NAME} G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {ensure_webhook()} IST:{get_ist_time()}",200
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
            rt=reply_msg.get("text","") or reply_msg.get("caption","") or ""; rf=reply_msg.get("from",{}).get("first_name","")
            if rt: reply_context=f"{rf} ne kaha tha: '{rt}' - iska reply hai"
            if reply_msg.get("photo") and text:
                fbytes,_=tg_get_file_bytes(reply_msg["photo"][-1]["file_id"])
                if fbytes:
                    v=ask_gemini_vision(fbytes, f"User replied to this photo and says: {text}. Context: {reply_context}. Roman Hinglish me jawab do.");
                    if v: tg_send(chat_id,v,message_id); return "ok",200

        if msg.get("photo"):
            fbytes,_=tg_get_file_bytes(msg["photo"][-1]["file_id"])
            if fbytes:
                q=text if text else "Is photo me kya hai batao"; 
                if reply_context: q=f"{reply_context}\n{q}"
                v=ask_gemini_vision(fbytes,q); 
                if v: tg_send(chat_id,v,message_id)
                else: tg_send(chat_id,brain(text or "photo bheja",user_id,is_owner,uname,reply_context),message_id)
                return "ok",200

        media_id=None; media_name="voice.ogg"
        if msg.get("voice"): media_id=msg["voice"]["file_id"]
        elif msg.get("audio"): media_id=msg["audio"]["file_id"]; media_name="audio.mp3"
        elif msg.get("video"): media_id=msg["video"]["file_id"]; media_name="video.mp4"
        elif msg.get("video_note"): media_id=msg["video_note"]["file_id"]; media_name="video.mp4"

        if media_id:
            b,fp=tg_get_file_bytes(media_id)
            if not b: tg_send(chat_id,"File nahi mili, fir se bhejo.",message_id); return "ok",200
            heard=transcribe_media(b, fp.split("/")[-1] if fp else media_name)
            if heard:
                if is_owner: tg_send(chat_id,f"Suna: {heard}",message_id)
                tg_send(chat_id,brain(heard,user_id,is_owner,uname,reply_context),message_id)
            else:
                # Video ka vision
                v=ask_gemini_vision(b, text or "Is video me kya hai batao Roman Hinglish me")
                if v: tg_send(chat_id,v,message_id)
                else: tg_send(chat_id,"Awaz saaf nahi aayi.",message_id)
            return "ok",200

        if not text: return "ok",200
        ans=brain(text,user_id,is_owner,uname,reply_context)
        tg_send(chat_id,ans,message_id)
        return "ok",200
    except: print(traceback.format_exc()); return "ok",200
