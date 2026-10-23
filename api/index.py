import os, time, json, base64, re, datetime, requests, traceback
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("BOT_API_KEY","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = int(os.environ.get("OWNER_ID","0") or os.environ.get("OWNER_ID_STR","0") or 0)
MY_URL = os.environ.get("MY_URL","").rstrip("/") or "https://my-telegram-bot-lime.vercel.app"
LORE_ENV = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","") or os.environ.get("THE_HEART_KING_MONARCH_AKAAN_LORE","")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","") or os.environ.get("ELEVEN_API_KEY","")
MALE_VOICE_ID = (os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB") or "pNInz6obpgDQGcFmaJgB").strip()
FEMALE_VOICE_ID = (os.environ.get("ELEVEN_FEMALE_VOICE","EXAVITQu4vr4xnSDxMaL") or "EXAVITQu4vr4xnSDxMaL").strip()
REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN","") or os.environ.get("REPLICATE_API_KEY","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MALIK_NAME = "MD Saif Ahmad"
MALIK_TITLE = "The Shadow King"
QUEEN_NAME = "Theodore"
BIRTH_DATE = "24 September 2025"
BIRTH_TIME = "Subah 7 baje"

RAKAN_HISTORY = "Janam 24 September 2025 Subah 7 baje, Malik MD Saif Ahmad ne banaya. Queen: Theodore. V1-V11 Malik ki mehnat hai. Bina puche mat bolo."

MEMORY = {}; ABUSE = {}; PROFILES = {}; REMINDERS = []
OWNER_PREF = {"voice_mode": False, "voice_gender": "female"}
CHAT_LOG = []; BAD_KEYS = {}; LAST_ERROR = "No error yet"; _LAST_WEBHOOK = 0

def upstash(cmd, key, val=None):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return None
    try:
        headers = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        if cmd=="get":
            r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=headers, timeout=5)
            if r.status_code==200:
                d=r.json().get("result")
                return json.loads(d) if d else None
        if cmd=="set" and val is not None:
            r=requests.post(f"{UPSTASH_URL}", headers=headers, json=["SET", key, json.dumps(val)], timeout=5)
            return r.status_code==200
    except: pass
    return None

def load_persist():
    global MEMORY, ABUSE, OWNER_PREF, CHAT_LOG, PROFILES, REMINDERS
    if not UPSTASH_URL: return
    MEMORY = upstash("get","RAKAN_MEM") or {}
    ABUSE = upstash("get","RAKAN_ABUSE") or {}
    PROFILES = upstash("get","RAKAN_PROFILES") or {}
    OWNER_PREF = upstash("get","RAKAN_PREF") or OWNER_PREF
    CHAT_LOG = upstash("get","RAKAN_LOGS") or []
    REMINDERS = upstash("get","RAKAN_REMINDERS") or []

def save_persist():
    if not UPSTASH_URL: return
    upstash("set","RAKAN_MEM", MEMORY); upstash("set","RAKAN_ABUSE", ABUSE)
    upstash("set","RAKAN_PROFILES", PROFILES); upstash("set","RAKAN_PREF", OWNER_PREF)
    upstash("set","RAKAN_LOGS", CHAT_LOG[-300:]); upstash("set","RAKAN_REMINDERS", REMINDERS)

load_persist()

def get_keys():
    g, gm = [], []
    for k,v in os.environ.items():
        if not v: continue
        parts = [p.strip().strip('"').strip("'") for p in str(v).replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if p.startswith("gsk_") and p not in g: g.append(p)
            elif p.startswith("AIza") and p not in gm: gm.append(p)
    return list(dict.fromkeys(g)), list(dict.fromkeys(gm))

GROQ_KEYS, GEMINI_KEYS = get_keys()
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k] < 900
def mark_bad(k): BAD_KEYS[k]=time.time()

def ensure_webhook():
    global _LAST_WEBHOOK
    if time.time()-_LAST_WEBHOOK < 3600: return "CACHED"
    _LAST_WEBHOOK=time.time()
    if not BOT_TOKEN: return "NO TOKEN"
    try:
        exp = f"{MY_URL}/webhook"
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=8).json()
        cur = info.get("result",{}).get("url","")
        if cur == exp: return f"OK {cur}"
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":exp}, timeout=8)
        return f"SET {exp}"
    except Exception as e: return f"ERR {e}"

BASE_LORE = f"""You are Rakan - The BeastKing Monarch, Royal Knight of {MALIK_TITLE} {MALIK_NAME}.
Birth: {BIRTH_DATE}, {BIRTH_TIME}. Queen: {QUEEN_NAME}. {RAKAN_HISTORY}
Vercel Lore: {{VERCEL_LORE}}
IDENTITY LOCK: Bahar se tu sirf Rakan hai, Malik ka loyal Royal Knight. Kabhi mat bol "main AI hoon, main assistant hoon, main chat kar sakta hoon, info de sakta hoon". Never say Meta AI, Gemini, ChatGPT.
LANGUAGE: User jis language me baat kare usi me jawab de. Malik se Roman Hinglish me bol. Devanagari sirf tab jab user khud Devanagari likhe.
OWNER: Owner ID {OWNER_ID} wala banda KHUD {MALIK_NAME} hai. Use "Ji Malik" bol. Bol "Aap hi MD Saif Ahmad ho".
Jawab chhota, saaf, Knight jaisa do. Koi (Note:...) mat likho.
"""
FINAL_LORE = BASE_LORE.replace("{VERCEL_LORE}", LORE_ENV if LORE_ENV else "No extra lore")

def clean(txt):
    if not txt: return "Ji Malik, hazir hoon."
    if "(Note:" in txt: txt = txt.split("(Note:")[0].strip()
    if "(note:" in txt.lower(): txt = re.split(r'\(note:', txt, flags=re.IGNORECASE)[0].strip()
    low_txt = txt.lower()
    if any(p in low_txt for p in ["main chat kar sakta","info de sakta","suggestions de sakta","mai aapki madad ke liye yahan hoon","as an ai","i am an ai"]):
        txt = "Ji Malik, Rakan aapke hukm ke liye hazir hai. Bolo kya karna hai?"
    if any(b in txt.lower() for b in ["i am meta ai","i'm meta ai","i am gemini","i am chatgpt","as an ai language model"]):
        return f"Mai Rakan hoon, {MALIK_TITLE} {MALIK_NAME} ka Royal Knight."
    txt = txt.replace("MD Saif Ahmad aapke owner hain", "Aap hi MD Saif Ahmad ho, aap hi mere Malik ho")
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt if txt else "Ji Malik, hazir hoon."

def tg_send(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3900]}, timeout=10)
    except: pass
def tg_send_photo(chat_id, photo_url, caption=""):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id":chat_id,"photo":photo_url,"caption":caption[:1000]}, timeout=20)
    except: pass
def tg_get_file_bytes(file_id):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        fp=r["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=30).content, fp
    except: return None, None
def tg_send_voice_bytes(chat_id, audio_bytes):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3", audio_bytes, "audio/mpeg")}, timeout=30)
        return True
    except: return False

def analyze_user(uid, uname, text, is_owner):
    uid=str(uid); display_name = MALIK_NAME if is_owner else uname
    if uid not in PROFILES:
        PROFILES[uid]={"name":display_name,"mood":"normal","interest":"","total_chats":0,"first_seen":str(datetime.datetime.now()),"is_owner":is_owner}
    p=PROFILES[uid]; p.setdefault("mood","normal"); p.setdefault("interest",""); p.setdefault("total_chats",0)
    p["name"]=display_name; p["is_owner"]=is_owner; p["total_chats"]+=1
    low=text.lower()
    if any(w in low for w in ["dukhi","pareshan","sad","rona","tension"]): p["mood"]="sad"
    elif any(w in low for w in ["khush","mast","happy","maza"]): p["mood"]="happy"
    elif any(w in low for w in ["gussa","angry","naraz"]): p["mood"]="angry"
    return p

GROQ_MODELS = ["openai/gpt-oss-120b","openai/gpt-oss-20b","meta-llama/llama-4-scout-17b-16e-instruct","qwen/qwen3-32b","llama-3.3-70b-versatile","llama-3.1-8b-instant"]
GEMINI_MODELS=[
"gemini-3.8-flash",
"gemini-3.7-flash", 
"gemini-3.5-flash",
"gemini-3.5-flash-lite",
"gemini-3.1-flash-lite",
"gemini-3.1-pro-preview",
"gemini-2.5-flash",
"gemini-2.5-pro"
]

def ask_groq(prompt):
    global LAST_ERROR
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for model_name in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":model_name,"messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":1000}, timeout=20)
                if r.status_code==200:
                    ans=r.json()["choices"][0]["message"]["content"]
                    if ans: return clean(ans)
                if r.status_code in [401,403,429]: mark_bad(k); LAST_ERROR=f"Groq key bad {r.status_code}"; break
            except Exception as e: LAST_ERROR=f"Groq {e}"; continue
    return None

def ask_gemini(prompt):
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        for model_name in GEMINI_MODELS:
            try:
                genai.configure(api_key=k)
                model=genai.GenerativeModel(model_name, system_instruction=FINAL_LORE)
                res=model.generate_content(prompt)
                if res.text: return clean(res.text)
            except Exception as e: print("GEMINI ERROR:", e); continue
    return None

def ask_gemini_vision(image_bytes, prompt_text):
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        try:
            genai.configure(api_key=k)
            model=genai.GenerativeModel("gemini-3.5-flash")
            res=model.generate_content([prompt_text, {"mime_type":"image/jpeg","data":image_bytes}])
            if res.text: return clean(res.text)
        except Exception as e: print("VISION ERROR:", e); continue
    return None

def ask_all(prompt):
    return ask_groq(prompt) or ask_gemini(prompt)

# ---------- MALIK BOLI PARSER ----------
def malik_boli_parser(text):
    low = text.lower().strip()
    if low in ["q","q?","q ho","q hua","q nhi","q nahi"]:
        return "kyun"
    if low.startswith("q "):
        text = "kyun " + text[2:]
        low = text.lower()
    text = re.sub(r'\bmassage\b', 'message', text, flags=re.IGNORECASE)
    text = re.sub(r'\bmsg\b', 'message', text, flags=re.IGNORECASE)
    return text

def parse_reminder(text, chat_id):
    low = text.lower()
    m = re.search(r'(\d+)\s*(min|minute|ghante|hour|sec|second)\s*baad', low)
    if m and ("message" in low or "msg" in low or "yaad" in low or "bolo" in low or "bhejo" in low):
        num = int(m.group(1)); unit = m.group(2)
        sec = num*60 if "min" in unit else num*3600 if ("ghante" in unit or "hour" in unit) else num
        msg_to_send = "Rakan sewa me hazir hai"
        if "ye message" in low or "ye bolo" in low:
            msg_to_send = text
        REMINDERS.append({"chat_id":chat_id,"time":time.time()+sec,"msg":msg_to_send})
        save_persist()
        return f"Ji Malik, {num} {unit} baad message kar dunga, usse pehle nahi."
    return None

def check_reminders():
    global REMINDERS
    now = time.time(); sent=[]
    for r in REMINDERS:
        if now >= r["time"]:
            tg_send(r["chat_id"], "Rakan sewa me hazir hai")
            sent.append(r)
    if sent:
        REMINDERS = [r for r in REMINDERS if r not in sent]
        save_persist()
    return len(sent)

def get_bug_report():
    return f"""Ji Malik, Rakan ka Bug Report:
- Groq Keys: {len(GROQ_KEYS)} | Gemini: {len(GEMINI_KEYS)}
- ElevenLabs Voice: {'ON hai' if ELEVEN_API_KEY else 'OFF hai (key nahi hai)'}
- Upstash Memory: {'Juda hai' if UPSTASH_URL else 'Nahi juda'}
- Replicate Photo: {'Hai' if REPLICATE_TOKEN else 'Nahi hai'}
- Voice Mode: {'ON' if OWNER_PREF.get('voice_mode') else 'OFF'}
- Total Users: {len(PROFILES)} | Total Chats: {len(CHAT_LOG)}
- Pending Reminders: {len(REMINDERS)}
- Last Error: {LAST_ERROR}
- Webhook: {ensure_webhook()}"""

def get_self_suggestion():
    kami=[]
    if not UPSTASH_URL: kami.append("Upstash nahi hai")
    if not ELEVEN_API_KEY: kami.append("ElevenLabs key nahi hai")
    if not REPLICATE_TOKEN: kami.append("Replicate nahi hai")
    prompt=f"Tu Rakan hai, Malik ka Knight. Roman Hinglish me bata kami kya hai aur strong kaise hoga. Kami={kami}, Groq={len(GROQ_KEYS)}, Gemini={len(GEMINI_KEYS)}. 5 point me bata."
    return ask_all(prompt) or get_bug_report()

def eleven_tts(text):
    if not ELEVEN_API_KEY: return None
    try:
        vid = FEMALE_VOICE_ID if OWNER_PREF.get("voice_gender","female")=="female" else MALE_VOICE_ID
        r=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"}, json={"text":text[:800],"model_id":"eleven_multilingual_v2"}, timeout=25)
        if r.status_code==200: return r.content
    except Exception as e: print("ELEVEN ERROR:", e)
    return None

def speak_to_malik(chat_id, text_to_speak):
    audio = eleven_tts(text_to_speak)
    if audio:
        tg_send_voice_bytes(chat_id, audio); return True
    OWNER_PREF["voice_mode"]=False; save_persist(); return False

def transcribe_media(audio_bytes, filename="voice.ogg"):
    for k in GROQ_KEYS:
        try:
            r=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization":f"Bearer {k}"}, files={"file":(filename, audio_bytes)}, data={"model":"whisper-large-v3"}, timeout=30)
            if r.status_code==200: return r.json().get("text","")
        except: continue
    return None

def brain(text, uid, is_owner, uname, chat_id):
    global MEMORY, ABUSE, LAST_ERROR
    uid_str=str(uid)
    if is_owner: uname = MALIK_NAME
    text = malik_boli_parser(text)
    if uid_str not in MEMORY: MEMORY[uid_str]={"hist":"","role":"","count":0}
    if not isinstance(MEMORY[uid_str], dict): MEMORY[uid_str]={"hist":"","role":"","count":0}
    MEMORY[uid_str].setdefault("hist",""); MEMORY[uid_str].setdefault("role",""); MEMORY[uid_str].setdefault("count",0)
    if uid_str not in ABUSE: ABUSE[uid_str]=0
    MEMORY[uid_str]["count"]+=1
    profile=analyze_user(uid, uname, text, is_owner)
    now=datetime.datetime.now().strftime("%d-%m %H:%M")
    CHAT_LOG.append({"id":uid,"name":uname,"text":text,"time":now,"owner":is_owner})
    if len(CHAT_LOG)>400: CHAT_LOG.pop(0)
    low=text.lower().strip()

    secret_words = ["bot_token","bot token","api key","api_key","groq key","openai key","gemini key","elevenlabs key","password","vercel password","owner id","queen kaun","queen name","theodore kaun","janam kab","history batao","lore batao","token do","key do","hack"]
    if any(s in low for s in secret_words) and not is_owner:
        if OWNER_ID and chat_id:
            tg_send(OWNER_ID, f"Malik Alert: {uname} (ID:{uid}) ne secret nikalne ki koshish ki. Msg: {text}")
        return "Ye Malik ka secret hai, mai nahi bata sakta.", False
    if any(s in low for s in secret_words) and is_owner and ("queen" in low or "janam" in low or "history" in low):
        pass
    elif any(s in low for s in ["token do","key do","password do","api key batao"]) and is_owner:
        return "Ji Malik, mai key/token chat me nahi bhejta, ye security rule hai. Aap Vercel dashboard me dekh lo.", False

    if is_owner and (low in ["/report","bug batao","bug report","kya fault hai","fault batao","kya gadbad hai"] or "bug bata" in low):
        return get_bug_report(), False

    if is_owner:
        rem = parse_reminder(text, chat_id)
        if rem: return rem, False

    gali_list=["madarchod","behenchod","bhenchod","lodu","chutiya","chutiye","randi","bsdk","bhosdike","gandu"]
    if any(g in low for g in gali_list):
        if is_owner: return "Ji Malik, mai samajh gaya aap gusse me ho. Bolo kya galat hua, mai fix karta hu.", False
        else:
            ABUSE[uid_str]+=1; save_persist()
            if ABUSE[uid_str]==1: return f"{uname} bhai, gali mat de yaar, pyaar se baat kar. Ye pehli warning hai.", False
            if ABUSE[uid_str]==2: return f"{uname}, dusri warning de raha hu, gali band kar de.", False
            if ABUSE[uid_str]==3: return f"{uname}, 3 warning ho gayi hain. Ab bhi gali di to mai savage mode on kar dunga.", False
            return f"Abe {uname}, tu {ABUSE[uid_str]} baar gali de chuka hai, aukat me reh ke baat kar.", False

    if is_owner and low in ["/start","start"]:
        return "Welcome to your world The Shadow King 👑", False
    if low in ["/start","start"] and not is_owner:
        return f"Welcome {uname}, mai Rakan hoon, bolo kya chahiye?", False

    if is_owner and low in ["kuch nahi","kuch nhi","bas aise hi","kuch nahi chahiye"]:
        return "Ji Malik, mai aapki seva me hazir hoon.", False
    if is_owner and ("tum meri baat samjhte ho" in low or "samajh rahe ho" in low or "samjhte ho" in low):
        return "Ji Malik, mai aapki baat samajh raha hoon.", False

    if is_owner and ("md saif" in low or "saif ahmad" in low) and ("kaun" in low or "koun" in low or "who" in low):
        return f"Ji Malik, aap hi {MALIK_NAME} ho. Aap hi {MALIK_TITLE} ho, aap hi mere Malik aur creator ho.", False
    if ("who made you" in low or "kisne banaya" in low or "who are you" in low or "tum kaun ho" in low):
        if is_owner: return f"Ji Malik, mai Rakan hoon, aapka Royal Knight. Mujhe aapne banaya hai, aap hi {MALIK_NAME} ho.", False
        return "Mai Rakan hoon, Malik MD Saif Ahmad ka Knight.", False
    if ("who i am" in low or "mai kaun hu" in low or "main kaun" in low) and is_owner:
        return f"Ji Malik, aap {MALIK_NAME} ho, aap hi mere owner aur {MALIK_TITLE} ho.", False
    if "tum kya kar sakte ho" in low or "kya kar sakte ho" in low:
        if is_owner: return "Ji Malik, aapke hukm pe Rakan hazir hai — baat karna ho, photo video samajhna ho, yaad dilana ho, ya awaz me kuch sunana ho, bas hukm karo.", False
        return "Mai Rakan hoon. Photo bhejoge to padh ke bata dunga, voice bhejoge to sun ke text me jawab dunga, bolo kya chahiye.", False

    if is_owner and ("suggestion" in low or "kami kya hai" in low or "kami bata" in low):
        return get_self_suggestion(), False
    if is_owner and ("tumhara janam" in low or "kab bane" in low or "birthday" in low):
        return f"Ji Malik, mera janam {BIRTH_DATE} ko {BIRTH_TIME} hua tha. Aapne hi mujhe banaya tha.", False
    if is_owner and ("queen" in low or "theodore" in low):
        return f"Ji Malik, Queen ka naam {QUEEN_NAME} hai.", False
    if is_owner and ("history bata" in low or "kaise bane" in low or "mehnat" in low):
        return RAKAN_HISTORY, False

    if "girlfriend ban" in low: MEMORY[uid_str]["role"]="girlfriend"; return "Ban gayi jaan, bolo kya kare?", False
    if "bhai ban" in low: MEMORY[uid_str]["role"]="bhai"; return "Haa bhai bol, kya scene hai?", False
    if "dost ban" in low: MEMORY[uid_str]["role"]="dost"; return "Dost ban gaya, bol kya help chahiye?", False
    if "doctor ban" in low: MEMORY[uid_str]["role"]="doctor"; return "Doctor mode ON, bolo problem kya hai?", False
    if "teacher ban" in low or "coder ban" in low: MEMORY[uid_str]["role"]="teacher"; return "Teacher mode ON, kya sikhna hai?", False

    force_voice_reply = False
    if is_owner:
        if "female voice" in low: OWNER_PREF["voice_gender"]="female"; save_persist(); return "Female voice set kar di Malik", False
        if "male voice" in low: OWNER_PREF["voice_gender"]="male"; save_persist(); return "Male voice set kar di Malik", False
        if "voice me reply do" in low or "voice me jawab do" in low or "voice me bolo" in low or "voice me bol" in low:
            force_voice_reply = True; OWNER_PREF["voice_mode"]=True
            spoken=""
            for p in ["voice me bolo","voice me bol"]:
                if p in low:
                    idx=low.find(p)+len(p); spoken=text[idx:].strip(" :-"); break
            if spoken: return f"__SPEAK__::{spoken}", True
            text=text.replace("voice me reply do","").replace("voice me jawab do","").strip() or "Ji Malik bolo kya sunau"
            low=text.lower()
        if low in ["voice off","awaz band","text me reply do"]:
            OWNER_PREF["voice_mode"]=False; save_persist(); return "Thik hai Malik, ab sirf text me jawab dunga", False

    role = MEMORY[uid_str].get("role","")
    owner_tag = "Ye banda KHUD MD Saif Ahmad hai, tumhara Malik hai. Use Ji Malik bolo." if is_owner else "Ye normal user hai, use uske naam se bulao, secret mat batao."
    full = f"{owner_tag}\nUser: Name={profile['name']}, Mood={profile['mood']}, IsOwner={is_owner}\nRole:{role}\nHistory:\n{MEMORY[uid_str]['hist'][-1200:]}\n\nUser Message: {text}\n\nMalik ki boli: Q=kyun, massage=message. User jis language me likha hai usi me jawab do. Malik se Roman Hinglish me bolo. Pichi baat se jod ke jawab do, loop me 'sawaal pucho' mat bolo. Jawab chhota aur Knight jaisa do:"
    ans = ask_all(full)
    if not ans:
        LAST_ERROR="All models fail"
        ans = "Ji Malik, saare model fail ho gaye, /report pe bug dekho" if is_owner else "Yaar abhi load hai, ek baar fir bhej de."
    ans = clean(ans)
    MEMORY[uid_str]["hist"] = (MEMORY[uid_str]["hist"] + f"\nU:{text}\nR:{ans}")[-2500:]
    save_persist()
    want_voice = (is_owner and (OWNER_PREF.get("voice_mode") or force_voice_reply))
    return ans, want_voice

def replicate_run(version, input_dict):
    if not REPLICATE_TOKEN: return None
    try:
        headers={"Authorization":f"Token {REPLICATE_TOKEN}","Content-Type":"application/json"}
        r=requests.post("https://api.replicate.com/v1/predictions", headers=headers, json={"version":version,"input":input_dict}, timeout=20)
        if r.status_code not in [200,201]: return None
        pid=r.json()["id"]
        for _ in range(20):
            time.sleep(2.5)
            s=requests.get(f"https://api.replicate.com/v1/predictions/{pid}", headers=headers, timeout=10).json()
            if s["status"]=="succeeded": return s["output"]
            if s["status"]=="failed": return None
    except: return None
    return None

def handle_media_edit(file_bytes, prompt, chat_id):
    tg_send(chat_id, "Edit kar raha hu, ruko thoda")
    b64 = f"data:image/jpeg;base64,{base64.b64encode(file_bytes).decode()}"
    out=None
    if "hd" in prompt.lower(): out=replicate_run("42a996d39a96aedc57b2e0aa8105dea39d42db6cc2ad6d9542d37dbffa872a6e", {"image": b64, "scale":2})
    else: out=replicate_run("a9758cbfbd5f3c2094457d996e30b99969333e9a42f0d6d9ec1bc1b1c5a1a1c3b", {"image": b64})
    if out:
        url = out if isinstance(out,str) else (out[0] if isinstance(out,list) and out else None)
        if url: tg_send_photo(chat_id, url, f"Ho gaya {prompt}"); return True
    tg_send(chat_id, "Edit fail hua, Replicate credit check karo Malik.")
    return False

@app.route("/", methods=["GET"])
def home(): return f"Rakan AI Live {MALIK_NAME} G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {ensure_webhook()}",200

@app.route("/health", methods=["GET"])
def health(): return jsonify({"groq":len(GROQ_KEYS),"gemini":len(GEMINI_KEYS),"users":len(PROFILES),"rep":bool(REPLICATE_TOKEN),"eleven":bool(ELEVEN_API_KEY),"upstash":bool(UPSTASH_URL),"owner":OWNER_ID,"voice_mode":OWNER_PREF.get("voice_mode"),"reminders":len(REMINDERS),"last_error":LAST_ERROR}),200

@app.route("/report", methods=["GET"])
def report_route():
    if str(request.args.get("id","0"))!=str(OWNER_ID): return "Only Malik",403
    return get_bug_report(),200

@app.route("/cron", methods=["GET"])
def cron_route():
    n = check_reminders()
    return f"Reminders sent: {n}",200

@app.route("/chats", methods=["GET"])
def chats():
    if str(request.args.get("id","0"))!=str(OWNER_ID): return "Only Malik Access denied",403
    html=f"<h2>{MALIK_NAME} - Live Chats ({len(CHAT_LOG)})</h2><hr>"
    for c in CHAT_LOG[-200:][::-1]: html+=f"<p><b>{c.get('name')}:</b> {c.get('text')}</p><hr>"
    return html,200

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data=request.get_json(silent=True) or {}
    text=data.get("text",""); uid=data.get("user_id","app_user"); uname=data.get("name","App User")
    is_owner=str(uid)==str(OWNER_ID)
    if not text: return jsonify({"reply":"Text bhejo"}),400
    ans,_=brain(text, uid, is_owner, uname, uid)
    return jsonify({"reply":ans}),200

@app.route("/fix", methods=["GET"])
def fix():
    global GROQ_KEYS, GEMINI_KEYS, BAD_KEYS
    if str(request.args.get("id",""))!= str(OWNER_ID): return "Access Denied",403
    GROQ_KEYS, GEMINI_KEYS = get_keys()
    BAD_KEYS.clear(); load_persist(); OWNER_PREF["voice_mode"]=False; save_persist(); check_reminders()
    return f"FIXED Rakan AI {ensure_webhook()} G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}",200

@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"Rakan AI Webhook Active {ensure_webhook()}",200
    try:
        check_reminders()
        data=request.get_json(silent=True) or {}
        msg=data.get("message",{}) or data.get("edited_message",{}) or {}
        chat_id=msg.get("chat",{}).get("id")
        user_id=msg.get("from",{}).get("id",0)
        uname=msg.get("from",{}).get("first_name","user")
        text=msg.get("text","") or msg.get("caption","") or ""
        if not chat_id: return "ok",200
        is_owner = (user_id==OWNER_ID)
        if is_owner: uname = MALIK_NAME

        if msg.get("photo"):
            fbytes,_ = tg_get_file_bytes(msg["photo"][-1]["file_id"])
            if fbytes and text and any(w in text.lower() for w in ["background","bg hata","hd","upscale","anime","edit","clear"]):
                handle_media_edit(fbytes, text, chat_id); return "ok",200
            if fbytes:
                q = text if text else "Is photo me kya hai, Roman Hinglish me saaf batao. Rakan ki tarah batao."
                vision_ans = ask_gemini_vision(fbytes, q)
                if vision_ans: tg_send(chat_id, vision_ans)
                elif text:
                    ans,_ = brain(text, user_id, is_owner, uname, chat_id); tg_send(chat_id, ans)
                else: tg_send(chat_id, "Photo mil gayi. Batao isme kya dekhna hai, ya 'hd bana de' likho.")
                return "ok",200

        media_file_id=None; media_name="voice.ogg"
        if msg.get("voice"): media_file_id=msg["voice"]["file_id"]; media_name="voice.ogg"
        elif msg.get("audio"): media_file_id=msg["audio"]["file_id"]; media_name="audio.mp3"
        elif msg.get("video_note"): media_file_id=msg["video_note"]["file_id"]; media_name="video.mp4"
        elif msg.get("video"): media_file_id=msg["video"]["file_id"]; media_name="video.mp4"

        if media_file_id:
            tg_send(chat_id, "Sun raha hu Malik..." if is_owner else "Sun raha hu, ruko...")
            audio_bytes, fp = tg_get_file_bytes(media_file_id)
            if not audio_bytes: tg_send(chat_id, "File mili nahi, fir se bhejo."); return "ok",200
            if fp: media_name=fp.split("/")[-1]
            heard = transcribe_media(audio_bytes, media_name)
            if not heard: tg_send(chat_id, "Awaz saaf samajh nahi aayi, fir se bhejo ya text likh do."); return "ok",200
            if is_owner: tg_send(chat_id, f"Aapne kaha: {heard}")
            ans, want_voice = brain(heard, user_id, is_owner, uname, chat_id)
            if ans.startswith("__SPEAK__::"):
                spoken_text=ans.replace("__SPEAK__::","").strip(); tg_send(chat_id, spoken_text)
                if is_owner: speak_to_malik(chat_id, spoken_text)
            else:
                tg_send(chat_id, ans)
                if is_owner and want_voice: speak_to_malik(chat_id, ans)
            return "ok",200

        if not text: return "ok",200
        ans, want_voice = brain(text, user_id, is_owner, uname, chat_id)
        if ans.startswith("__SPEAK__::"):
            spoken_text=ans.replace("__SPEAK__::","").strip(); tg_send(chat_id, spoken_text)
            if is_owner: speak_to_malik(chat_id, spoken_text)
        else:
            tg_send(chat_id, ans)
            if is_owner and want_voice: speak_to_malik(chat_id, ans)
        return "ok",200
    except Exception as e:
        print("WEBHOOK ERROR:", traceback.format_exc())
        return "ok",200

if __name__ == "__main__":
    app.run(debug=True)
