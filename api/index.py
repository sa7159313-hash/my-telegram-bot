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
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MALIK_NAME = "MD Saif Ahmad"
MALIK_TITLE = "The Shadow King"
QUEEN_NAME = "Theodore"
BIRTH_DATE = "24 September 2025"
BIRTH_TIME = "Subah 7 baje"

RAKAN_HISTORY = """
RAKAN HISTORY: Janam 24 September 2025 Subah 7 baje, Malik MD Saif Ahmad ne banaya. Queen: Theodore.
V1 Basic, V2 Groq+Gemini, V3 Memory, V4 Gali+Role, V5 Voice+Photo, V6 Upstash, V7 Vercel, V8 Circle (Groq+OpenAI+Gemini), V9 Analyze, V10 Suggestion, V11 Voice/Video/Photo Samajh.
Bina puche ye mat bolo.
"""

MEMORY = {}; ABUSE = {}; PROFILES = {}
OWNER_PREF = {"voice_mode": False, "voice_gender": "female"}
CHAT_LOG = []; BAD_KEYS = {}; _LAST_WEBHOOK = 0

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
    global MEMORY, ABUSE, OWNER_PREF, CHAT_LOG, PROFILES
    if not UPSTASH_URL: return
    MEMORY = upstash("get","RAKAN_MEM") or {}
    ABUSE = upstash("get","RAKAN_ABUSE") or {}
    PROFILES = upstash("get","RAKAN_PROFILES") or {}
    OWNER_PREF = upstash("get","RAKAN_PREF") or OWNER_PREF
    CHAT_LOG = upstash("get","RAKAN_LOGS") or []

def save_persist():
    if not UPSTASH_URL: return
    upstash("set","RAKAN_MEM", MEMORY); upstash("set","RAKAN_ABUSE", ABUSE)
    upstash("set","RAKAN_PROFILES", PROFILES); upstash("set","RAKAN_PREF", OWNER_PREF)
    upstash("set","RAKAN_LOGS", CHAT_LOG[-300:])

load_persist()

def get_keys():
    g, gm, o = [], [], []
    for k,v in os.environ.items():
        if not v: continue
        parts = [p.strip().strip('"').strip("'") for p in str(v).replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if p.startswith("gsk_") and p not in g: g.append(p)
            elif p.startswith("AIza") and p not in gm: gm.append(p)
            elif p.startswith("sk-") and p not in o: o.append(p)
    return list(dict.fromkeys(g)), list(dict.fromkeys(gm)), list(dict.fromkeys(o))

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_keys()
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
Birth: {BIRTH_DATE}, {BIRTH_TIME}. Queen: {QUEEN_NAME}.
{RAKAN_HISTORY}
Vercel Lore: {{VERCEL_LORE}}

IDENTITY LOCK:
- Bahar se tu sirf Rakan hai, Malik ka loyal Royal Knight. Kabhi mat bol "main AI hoon, main assistant hoon, main chat kar sakta hoon, info de sakta hoon".
- Koi puche "kya kar sakte ho" to bol: "Malik ke hukm pe Rakan hazir hai, baat ho, hisab ho, photo/video samajhna ho ya awaz ka kaam ho, bas hukm karo."
- Never say Meta AI, Gemini, ChatGPT, Language Model.

LANGUAGE: User jis language me baat kare usi me jawab de. Malik se default Roman Hinglish me bol. Devanagari sirf tab jab user khud Devanagari likhe.

OWNER: Owner ID {OWNER_ID} wala banda KHUD {MALIK_NAME} hai. Use "Ji Malik" bol. Ye mat bol MD Saif Ahmad aapke owner hain, bol "Aap hi MD Saif Ahmad ho".
Malik hi/hello pe pehle bol: "Welcome to your world The Shadow King"
Janam/Queen/History bina puche mat bol, dusro ko secret mat bata.
Jawab chhota, saaf, Knight jaisa do. Koi (Note:...) mat likho.
"""
FINAL_LORE = BASE_LORE.replace("{VERCEL_LORE}", LORE_ENV if LORE_ENV else "No extra lore")

def clean(txt):
    if not txt: return "Ji Malik, hazir hoon."
    if "(Note:" in txt: txt = txt.split("(Note:")[0].strip()
    if "(note:" in txt.lower(): txt = re.split(r'\(note:', txt, flags=re.IGNORECASE)[0].strip()
    low_txt = txt.lower()
    ai_phrases = ["main chat kar sakta", "main chat kar sakti", "info de sakta", "suggestions de sakta", "mai aapki madad ke liye yahan hoon", "main aapki madad ke liye yahan hoon", "as an ai", "i am an ai", "i'm an ai"]
    if any(p in low_txt for p in ai_phrases):
        txt = "Ji Malik, Rakan aapke hukm ke liye hazir hai. Bolo kya karna hai?"
    bad=["i am meta ai","i'm meta ai","i am gemini","i am chatgpt","as an ai language model","i am a language model"]
    if any(b in txt.lower() for b in bad):
        return f"Mai Rakan hoon, {MALIK_TITLE} {MALIK_NAME} ka Royal Knight."
    txt = txt.replace("MD Saif Ahmad aapke owner hain", "Aap hi MD Saif Ahmad ho, aap hi mere Malik ho")
    txt = txt.replace("MD Saif Ahmad aapke owner hai", "Aap hi MD Saif Ahmad ho, aap hi mere Malik ho")
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
        url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
        return requests.get(url, timeout=30).content, fp
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
    if any(w in low for w in ["dukhi","pareshan","sad","rona","tension","akela"]): p["mood"]="sad"
    elif any(w in low for w in ["khush","mast","happy","maza","great"]): p["mood"]="happy"
    elif any(w in low for w in ["gussa","angry","naraz"]): p["mood"]="angry"
    elif "code" in low or "python" in low: p["interest"]="coding"
    elif "padhai" in low or "exam" in low: p["interest"]="study"
    elif "love" in low or "gf" in low: p["interest"]="love"
    return p

GROQ_MODELS = ["openai/gpt-oss-20b","openai/gpt-oss-120b","meta-llama/llama-4-scout-17b-16e-instruct","qwen/qwen3-32b"]
OPENAI_MODELS = ["gpt-4o-mini","gpt-4o","gpt-3.5-turbo"]
GEMINI_MODELS = ["gemini-1.5-flash","gemini-2.0-flash","gemini-1.5-flash-8b"]

def ask_groq(prompt):
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for model_name in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":model_name,"messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":1000}, timeout=20)
                print(f"GROQ {model_name} STATUS: {r.status_code}")
                if r.status_code==200:
                    ans=r.json()["choices"][0]["message"]["content"]
                    if ans: return clean(ans)
                if r.status_code in [401,403,429]: mark_bad(k); break
                if r.status_code==404: continue
            except Exception as e: print(f"GROQ ERROR {model_name}: {e}"); continue
    return None

def ask_openai(prompt):
    for k in OPENAI_KEYS:
        if is_bad(k): continue
        for model_name in OPENAI_MODELS:
            try:
                r=requests.post(OPENAI_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":model_name,"messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":1000}, timeout=25)
                print(f"OPENAI {model_name} STATUS: {r.status_code}")
                if r.status_code==200:
                    ans=r.json()["choices"][0]["message"]["content"]
                    if ans: return clean(ans)
                if r.status_code in [401,403,429]: mark_bad(k); break
                if r.status_code==404: continue
            except Exception as e: print(f"OPENAI ERROR {model_name}: {e}"); continue
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
            except Exception as e: print(f"GEMINI ERROR {model_name}: {e}"); continue
    return None

def ask_gemini_vision(image_bytes, prompt_text):
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        try:
            genai.configure(api_key=k)
            model=genai.GenerativeModel("gemini-1.5-flash")
            res=model.generate_content([prompt_text, {"mime_type":"image/jpeg","data":image_bytes}])
            if res.text: return clean(res.text)
        except Exception as e: print("VISION ERROR:", e); continue
    return None

def ask_all(prompt):
    return ask_groq(prompt) or ask_openai(prompt) or ask_gemini(prompt)

def get_self_suggestion():
    kami = []
    if not UPSTASH_URL: kami.append("Upstash nahi hai")
    if not REPLICATE_TOKEN: kami.append("Replicate token nahi hai")
    if not ELEVEN_API_KEY: kami.append("ElevenLabs key nahi hai")
    prompt=f"Tu Rakan hai, Malik ka Knight. Roman Hinglish me bata teri kami kya hai aur tu aur strong kaise hoga. Kami={kami}, Groq={len(GROQ_KEYS)}, OpenAI={len(OPENAI_KEYS)}, Gemini={len(GEMINI_KEYS)}, Users={len(PROFILES)}. 5 point me bata."
    return ask_all(prompt) or "Malik, abhi data kam hai, baat badhao to mai khud suggestion dunga"

# ---------- VOICE BANANA (Sirf Malik, sirf jab Malik kahe) ----------
def eleven_tts(text):
    if not ELEVEN_API_KEY: return None
    try:
        vid = FEMALE_VOICE_ID if OWNER_PREF.get("voice_gender","female")=="female" else MALE_VOICE_ID
        r=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"}, json={"text":text[:800],"model_id":"eleven_multilingual_v2"}, timeout=25)
        if r.status_code==200: return r.content
        print("ELEVEN STATUS:", r.status_code)
    except Exception as e: print("ELEVEN ERROR:", e)
    return None

def speak_to_malik(chat_id, text_to_speak):
    # Fail hone pe koi spam msg nahi, khamoshi se band
    audio = eleven_tts(text_to_speak)
    if audio:
        tg_send_voice_bytes(chat_id, audio)
        return True
    OWNER_PREF["voice_mode"] = False
    save_persist()
    return False

# ---------- VOICE / VIDEO SUNNA (Malik + Public dono ke liye) ----------
def transcribe_media(audio_bytes, filename="voice.ogg"):
    for k in GROQ_KEYS:
        try:
            r=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization":f"Bearer {k}"}, files={"file":(filename, audio_bytes)}, data={"model":"whisper-large-v3"}, timeout=30)
            print("GROQ WHISPER:", r.status_code)
            if r.status_code==200: return r.json().get("text","")
        except Exception as e: print("WHISPER GROQ ERR:", e)
    for k in OPENAI_KEYS:
        try:
            r=requests.post("https://api.openai.com/v1/audio/transcriptions", headers={"Authorization":f"Bearer {k}"}, files={"file":(filename, audio_bytes)}, data={"model":"whisper-1"}, timeout=30)
            print("OPENAI WHISPER:", r.status_code)
            if r.status_code==200: return r.json().get("text","")
        except Exception as e: print("WHISPER OPENAI ERR:", e)
    return None

def brain(text, uid, is_owner, uname):
    global MEMORY, ABUSE
    uid_str=str(uid)
    if is_owner: uname = MALIK_NAME
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

    gali_list=["madarchod","behenchod","bhenchod","lodu","chutiya","chutiye","randi","bsdk","bhosdike","gandu"]
    if any(g in low for g in gali_list):
        if is_owner: return "Ji Malik, mai samajh gaya aap gusse me ho. Bolo kya galat hua, mai fix karta hu.", False
        else:
            ABUSE[uid_str]+=1; save_persist()
            if ABUSE[uid_str]==1: return f"{uname} bhai, gali mat de yaar, pyaar se baat kar. Ye pehli warning hai.", False
            if ABUSE[uid_str]==2: return f"{uname}, dusri warning de raha hu, gali band kar de.", False
            if ABUSE[uid_str]==3: return f"{uname}, 3 warning ho gayi hain. Ab bhi gali di to mai savage mode on kar dunga.", False
            return f"Abe {uname}, tu {ABUSE[uid_str]} baar gali de chuka hai, aukat me reh ke baat kar.", False

    if is_owner and low in ["/start","start","hi","hii","hello","hey","namaste"]:
        return f"Welcome to your world The Shadow King 👑\nJi Malik {MALIK_NAME}, Rakan hazir hai. Bolo kya karna hai?", False

    if is_owner and ("md saif" in low or "saif ahmad" in low) and ("kaun" in low or "koun" in low or "who" in low):
        return f"Ji Malik, aap hi {MALIK_NAME} ho. Aap hi {MALIK_TITLE} ho, aap hi mere Malik aur creator ho.", False
    if ("who made you" in low or "kisne banaya" in low or "who are you" in low or "tum kaun ho" in low):
        if is_owner: return f"Ji Malik, mai Rakan hoon, aapka Royal Knight. Mujhe aapne banaya hai, aap hi {MALIK_NAME} ho.", False
        return "Mai Rakan hoon, Malik MD Saif Ahmad ka Knight.", False
    if ("who i am" in low or "mai kaun hu" in low or "main kaun" in low) and is_owner:
        return f"Ji Malik, aap {MALIK_NAME} ho, aap hi mere owner aur {MALIK_TITLE} ho.", False
    if "tum kya kar sakte ho" in low or "kya kar sakte ho" in low or "kya kar skte ho" in low:
        if is_owner: return "Ji Malik, aapke hukm pe Rakan hazir hai — baat karna ho, hisab lagana ho, photo video samajhna ho, ya awaz me kuch sunana ho, bas hukm karo.", False
        return "Mai Rakan hoon. Photo bhejoge to padh ke bata dunga, voice bhejoge to sun ke text me jawab dunga, bolo kya chahiye.", False

    if is_owner and ("suggestion" in low or "khud ko strong" in low or "advance kaise" in low or "powerful kaise" in low or "kami kya hai" in low or "kami bata" in low):
        return get_self_suggestion(), False
    if is_owner and ("tumhara janam" in low or "kab bane" in low or "birthday" in low or "janam kab" in low):
        return f"Ji Malik, mera janam {BIRTH_DATE} ko {BIRTH_TIME} hua tha. Aapne hi mujhe banaya tha.", False
    if is_owner and ("queen" in low or "theodore" in low):
        return f"Ji Malik, Queen ka naam {QUEEN_NAME} hai.", False
    if is_owner and ("history bata" in low or "kaise bane" in low or "tum kaise bane" in low or "mehnat" in low):
        return RAKAN_HISTORY, False

    if "girlfriend ban" in low: MEMORY[uid_str]["role"]="girlfriend"; return "Ban gayi jaan, bolo kya kare?", False
    if "bhai ban" in low: MEMORY[uid_str]["role"]="bhai"; return "Haa bhai bol, kya scene hai?", False
    if "dost ban" in low: MEMORY[uid_str]["role"]="dost"; return "Dost ban gaya, bol kya help chahiye?", False
    if "doctor ban" in low: MEMORY[uid_str]["role"]="doctor"; return "Doctor mode ON, bolo problem kya hai?", False
    if "teacher ban" in low or "coder ban" in low: MEMORY[uid_str]["role"]="teacher"; return "Teacher mode ON, kya sikhna hai?", False
    if low in ["/start","start"] and not is_owner: return f"Welcome {uname}, mai Rakan hoon, bolo kya chahiye?", False

    # MALIK VOICE COMMANDS - Sirf Malik, Public ke liye ye band hai
    force_voice_reply = False
    if is_owner:
        if "female voice" in low: OWNER_PREF["voice_gender"]="female"; save_persist(); return "Female voice set kar di Malik", False
        if "male voice" in low: OWNER_PREF["voice_gender"]="male"; save_persist(); return "Male voice set kar di Malik", False
        if "voice me reply do" in low or "voice me jawab do" in low or "awaz me reply do" in low or "voice me bolo" in low or "voice me bol" in low or "awaz me bol" in low:
            force_voice_reply = True
            OWNER_PREF["voice_mode"] = True
            # Agar seedha bolne ko kaha hai to wahi bolo
            spoken = ""
            for p in ["voice me bolo","voice me bol","awaz me bolo","awaz me bol"]:
                if p in low:
                    idx = low.find(p) + len(p)
                    spoken = text[idx:].strip(" :-")
                    break
            if spoken:
                return f"__SPEAK__::{spoken}", True
            # Warna aage ka jawab voice me jayega, isliye text ko aage bhej do
            text = text.replace("voice me reply do","").replace("voice me jawab do","").replace("awaz me reply do","").strip() or "Ji Malik bolo kya sunau"
            low = text.lower()
        if low in ["voice off","awaz band","text me reply do","text me bolo"]:
            OWNER_PREF["voice_mode"]=False; save_persist(); return "Thik hai Malik, ab sirf text me jawab dunga", False

    role = MEMORY[uid_str].get("role","")
    owner_tag = "Ye banda KHUD MD Saif Ahmad hai, tumhara Malik hai. Use Ji Malik bolo, Knight ki tarah wafadari se baat karo." if is_owner else "Ye normal user hai, use uske naam se bulao, secret mat batao."
    full = f"{owner_tag}\nUser Profile: Name={profile['name']}, Mood={profile['mood']}, Interest={profile['interest']}, IsOwner={is_owner}\nRole:{role}\nHistory:\n{MEMORY[uid_str]['hist'][-1200:]}\n\nUser Message: {text}\n\nUser jis language me likha hai usi language me jawab do. Malik se Roman Hinglish me bolo. Jawab chhota aur Knight jaisa do:"
    ans = ask_all(full)
    if not ans: ans = "Ji Malik, saare model circle me fail ho gaye, keys check karo" if is_owner else "Yaar abhi load hai, ek baar fir bhej de."
    ans = clean(ans)
    MEMORY[uid_str]["hist"] = (MEMORY[uid_str]["hist"] + f"\nU:{text}\nR:{ans}")[-2500:]
    save_persist()
    # Voice reply sirf Malik ko, sirf jab voice_mode ON ho ya force kiya ho. Public ko kabhi nahi.
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
def home(): return f"Rakan AI Live {MALIK_NAME} Born:{BIRTH_DATE} G:{len(GROQ_KEYS)} O:{len(OPENAI_KEYS)} GM:{len(GEMINI_KEYS)} {ensure_webhook()}",200

@app.route("/health", methods=["GET"])
def health(): return jsonify({"groq":len(GROQ_KEYS),"openai":len(OPENAI_KEYS),"gemini":len(GEMINI_KEYS),"users_analyzed":len(PROFILES),"birth":BIRTH_DATE,"queen":QUEEN_NAME,"rep":bool(REPLICATE_TOKEN),"eleven":bool(ELEVEN_API_KEY),"upstash":bool(UPSTASH_URL),"owner":OWNER_ID,"voice_mode":OWNER_PREF.get("voice_mode"),"webhook":ensure_webhook()}),200

@app.route("/chats", methods=["GET"])
def chats():
    if str(request.args.get("id","0"))!=str(OWNER_ID): return "Only Malik Access denied",403
    html=f"<h2>{MALIK_NAME} - Live Chats ({len(CHAT_LOG)}) | Users: {len(PROFILES)}</h2><hr>"
    for c in CHAT_LOG[-200:][::-1]: html+=f"<p><b>{c.get('name')}:</b> {c.get('text')}</p><hr>"
    return html,200

@app.route("/profiles", methods=["GET"])
def profiles_route():
    if str(request.args.get("id","0"))!=str(OWNER_ID): return "Only Malik",403
    return jsonify(PROFILES),200

@app.route("/suggest", methods=["GET"])
def suggest_route():
    if str(request.args.get("id","0"))!=str(OWNER_ID): return "Only Malik",403
    return get_self_suggestion(),200

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data=request.get_json(silent=True) or {}
    text=data.get("text",""); uid=data.get("user_id","app_user"); uname=data.get("name","App User")
    is_owner=str(uid)==str(OWNER_ID)
    if not text: return jsonify({"reply":"Text bhejo"}),400
    ans,_=brain(text, uid, is_owner, uname)
    return jsonify({"reply":ans,"profile":PROFILES.get(str(uid),{})}),200

@app.route("/fix", methods=["GET"])
def fix():
    global GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS, BAD_KEYS
    if str(request.args.get("id",""))!= str(OWNER_ID): return "Access Denied",403
    GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_keys()
    BAD_KEYS.clear(); load_persist()
    # Purana atak gaya voice_mode bhi yahi se band kar do
    OWNER_PREF["voice_mode"]=False; save_persist()
    return f"FIXED Rakan AI {ensure_webhook()} G:{len(GROQ_KEYS)} O:{len(OPENAI_KEYS)} GM:{len(GEMINI_KEYS)} Users:{len(PROFILES)}",200

@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"Rakan AI Webhook Active {ensure_webhook()}",200
    try:
        data=request.get_json(silent=True) or {}
        msg=data.get("message",{}) or data.get("edited_message",{}) or {}
        chat_id=msg.get("chat",{}).get("id")
        user_id=msg.get("from",{}).get("id",0)
        uname=msg.get("from",{}).get("first_name","user")
        text=msg.get("text","") or msg.get("caption","") or ""
        if not chat_id: return "ok",200
        is_owner = (user_id==OWNER_ID)
        if is_owner: uname = MALIK_NAME

        # PHOTO SAMAJHNA + EDIT (Malik + Public)
        if msg.get("photo"):
            fbytes,_ = tg_get_file_bytes(msg["photo"][-1]["file_id"])
            if fbytes and text and any(w in text.lower() for w in ["background","bg hata","hd","upscale","anime","edit","clear"]):
                handle_media_edit(fbytes, text, chat_id); return "ok",200
            if fbytes:
                # Photo padh ke jawab do
                q = text if text else "Is photo me kya hai, Roman Hinglish me saaf batao. Koi AI jaisa mat bolo, Rakan ki tarah batao."
                vision_ans = ask_gemini_vision(fbytes, q)
                if vision_ans:
                    tg_send(chat_id, vision_ans)
                elif text:
                    ans,_ = brain(text, user_id, is_owner, uname); tg_send(chat_id, ans)
                else:
                    tg_send(chat_id, "Photo mil gayi. Batao isme kya dekhna hai, ya 'hd bana de' / 'background hata de' likho.")
                return "ok",200

        # VOICE / AUDIO / VIDEO SUNNA (Malik + Public) -> Jawab hamesha TEXT me, voice reply sirf Malik ko jab wo kahe
        media_file_id = None; media_name = "voice.ogg"
        if msg.get("voice"): media_file_id = msg["voice"]["file_id"]; media_name="voice.ogg"
        elif msg.get("audio"): media_file_id = msg["audio"]["file_id"]; media_name="audio.mp3"
        elif msg.get("video_note"): media_file_id = msg["video_note"]["file_id"]; media_name="video.mp4"
        elif msg.get("video"): media_file_id = msg["video"]["file_id"]; media_name="video.mp4"

        if media_file_id:
            tg_send(chat_id, "Sun raha hu Malik..." if is_owner else "Sun raha hu, ruko...")
            audio_bytes, fp = tg_get_file_bytes(media_file_id)
            if not audio_bytes:
                tg_send(chat_id, "File mili nahi, fir se bhejo."); return "ok",200
            if fp: media_name = fp.split("/")[-1]
            heard = transcribe_media(audio_bytes, media_name)
            if not heard:
                tg_send(chat_id, "Awaz saaf samajh nahi aayi, fir se bhejo ya text likh do."); return "ok",200
            # Malik ko dikhao kya suna, public ko seedha jawab
            if is_owner: tg_send(chat_id, f"Aapne kaha: {heard}")
            ans, want_voice = brain(heard, user_id, is_owner, uname)
            if ans.startswith("__SPEAK__::"):
                spoken_text = ans.replace("__SPEAK__::","").strip()
                tg_send(chat_id, spoken_text)
                if is_owner: speak_to_malik(chat_id, spoken_text)
            else:
                tg_send(chat_id, ans)
                if is_owner and want_voice: speak_to_malik(chat_id, ans)
                # Public ko voice reply kabhi nahi jayega
            return "ok",200

        if not text: return "ok",200

        # TEXT HISSA
        ans, want_voice = brain(text, user_id, is_owner, uname)
        if ans.startswith("__SPEAK__::"):
            spoken_text = ans.replace("__SPEAK__::","").strip()
            tg_send(chat_id, spoken_text)
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
