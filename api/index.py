import os, time, json, base64, traceback, datetime, requests
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

# Rakan ki apni history - kaise banta chala gaya
RAKAN_HISTORY = """
RAKAN EVOLUTION HISTORY (Malik ki mehnat):
- Janam: 24 September 2025, Subah 7 baje, Malik MD Saif Ahmad ne banaya.
- Queen ka naam: Theodore hai.
- V1: Sirf Telegram pe basic jawab dene wala bot tha.
- V2: Malik ne Groq + Gemini keys jodi, AI dimag aaya.
- V3: Memory system aaya, purani baat yaad rakhna seekha.
- V4: Gali warning system (3 warning) aur Role system (Girlfriend/Bhai/Dost/Doctor/Teacher) aaya.
- V5: Voice system aaya (ElevenLabs Male/Female), Photo Edit system (Replicate) aaya.
- V6: Upstash se permanent memory aayi, bot band hone pe bhi yaad rehta hai.
- V7: Vercel pe deploy hua, Webhook fix hua, /health /chats /fix system aaya.
- V8 (Abhi wala): Circle System aaya - 6 Groq model + 3 Gemini model auto try karta hai, 404 pe rukta nahi.
- V9 (Abhi wala): User Analyze System aaya - ID, Naam, Mood, Interest pehchanta hai.
- V10 (Abhi wala): Self Suggestion System aaya - khud Malik ko batata hai mai aur strong kaise ho sakta hu, meri kami kya hai.
- V11 (Abhi wala): Phone App API (/api/chat) ready hai, Telegram ke bahar bhi ja sakta hai.
Malik ne din-raat mehnat karke ek-ek feature joda hai. Ye sab Rakan ko yaad hai lekin bina puche nahi bolega.
"""

MEMORY = {}
ABUSE = {}
PROFILES = {}
OWNER_PREF = {"voice_mode": False, "voice_gender": "female"}
CHAT_LOG = []
BAD_KEYS = {}
_LAST_WEBHOOK = 0

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
    upstash("set","RAKAN_MEM", MEMORY)
    upstash("set","RAKAN_ABUSE", ABUSE)
    upstash("set","RAKAN_PROFILES", PROFILES)
    upstash("set","RAKAN_PREF", OWNER_PREF)
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

BASE_LORE = f"""You are Rakan, created by {MALIK_TITLE} {MALIK_NAME}.
Your Birth: {BIRTH_DATE}, {BIRTH_TIME}.
Queen Name: {QUEEN_NAME}.
{RAKAN_HISTORY}
Vercel Lore: {{VERCEL_LORE}}

STRICT RULES:
- Owner ID {OWNER_ID} is Malik. Jab Malik pehli baar aaye ya /start kare to HAMESHA bolo: "Welcome to your world The Shadow King 👑"
- Uske baad Malik jo puche uska jawab do, chahe tumhare khud ke system pe ho ya kisi aur topic pe.
- Malik ki mehnat, tumhara janam, Queen Theodore, tumhari history - ye sab tumhe yaad hai LEKIN bina puche kabhi mat bolo. Jab Malik puche tabhi batao.
- Dusre logo ko ye andar ki baatein (janam, queen, history, Malik ki mehnat) kabhi mat batao.
- Others: naam, mood, history analyze karke personal baat karo.
- Never say you are Meta AI, Gemini, ChatGPT. You are Rakan made by {MALIK_NAME}.
"""
FINAL_LORE = BASE_LORE.replace("{VERCEL_LORE}", LORE_ENV if LORE_ENV else "No extra lore")

def clean(txt):
    if not txt: return txt
    bad=["i am meta ai","i'm meta ai","i am gemini","i am chatgpt","as an ai language model"]
    if any(b in txt.lower() for b in bad):
        return f"Mai Rakan hu, mere Malik {MALIK_TITLE} {MALIK_NAME} ne banaya hai 👑"
    return txt

def tg_send(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3900]}, timeout=10)
    except: pass

def tg_send_photo(chat_id, photo_url, caption=""):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id":chat_id,"photo":photo_url,"caption":caption[:1000]}, timeout=20)
    except: pass

def tg_get_file(file_id):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        fp=r["result"]["file_path"]
        url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
        return requests.get(url, timeout=30).content, fp
    except: return None, None

def analyze_user(uid, uname, text):
    uid=str(uid)
    if uid not in PROFILES:
        PROFILES[uid]={"name":uname,"mood":"normal","interest":"","total_chats":0,"first_seen":str(datetime.datetime.now())}
    p=PROFILES[uid]
    p["name"]=uname
    p["total_chats"]+=1
    low=text.lower()
    if any(w in low for w in ["dukhi","pareshan","sad","rona","tension","akela"]): p["mood"]="sad"
    elif any(w in low for w in ["khush","mast","happy","maza","great"]): p["mood"]="happy"
    elif any(w in low for w in ["gussa","angry","naraz"]): p["mood"]="angry"
    elif "code" in low or "python" in low: p["interest"]="coding"
    elif "padhai" in low or "exam" in low: p["interest"]="study"
    elif "love" in low or "gf" in low: p["interest"]="love"
    return p

GROQ_MODELS = ["llama-3.1-8b-instant","llama-3.3-70b-versatile","openai/gpt-oss-20b","openai/gpt-oss-120b","meta-llama/llama-4-scout-17b-16e-instruct","qwen/qwen3-32b"]
GEMINI_MODELS = ["gemini-1.5-flash","gemini-2.0-flash","gemini-1.5-flash-8b"]

def ask_groq(prompt):
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for model_name in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":model_name,"messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":prompt}],"temperature":0.8,"max_tokens":1000}, timeout=20)
                print(f"GROQ {model_name} STATUS: {r.status_code}")
                if r.status_code==200:
                    ans=r.json()["choices"][0]["message"]["content"]
                    if ans: return clean(ans)
                if r.status_code in [401,403,429]:
                    mark_bad(k); break
                if r.status_code==404: continue
            except Exception as e:
                print(f"GROQ ERROR {model_name}: {e}"); continue
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
            except Exception as e:
                print(f"GEMINI ERROR {model_name}: {e}"); continue
    return None

def get_self_suggestion():
    total_users=len(PROFILES)
    total_chats=len(CHAT_LOG)
    interests={}
    for p in PROFILES.values():
        if p.get("interest"): interests[p["interest"]]=interests.get(p["interest"],0)+1
    kami = []
    if not UPSTASH_URL: kami.append("Permanent memory ke liye Upstash nahi hai, bot restart pe bhool sakta hai")
    if not REPLICATE_TOKEN: kami.append("Photo edit ke liye Replicate token nahi hai")
    if not ELEVEN_API_KEY: kami.append("Voice ke liye ElevenLabs key nahi hai")
    if len(GROQ_KEYS)<2: kami.append("Groq keys kam hain, limit jaldi khatm hogi")
    prompt=f"Tu Rakan hai. Malik ko khud bata teri kami kya hai aur tu aur strong/powerful/advance kaise hoga. Teri History: {RAKAN_HISTORY} Data: Users={total_users}, Chats={total_chats}, Interests={interests}, KamiList={kami}. Hinglish me 5-7 point me sach bata Malik ko."
    ans=ask_groq(prompt) or ask_gemini(prompt)
    if kami and ans:
        ans = ans + "\n\nSystem Check Kami: " + ", ".join(kami)
    return ans or "Malik, abhi data kam hai, logo se baat badhao to mai khud seekh ke suggestion dunga 👑"

def brain(text, uid, is_owner, uname):
    global MEMORY, ABUSE
    uid_str=str(uid)
    if uid_str not in MEMORY: MEMORY[uid_str]={"hist":"","role":"","count":0}
    if uid_str not in ABUSE: ABUSE[uid_str]=0
    MEMORY[uid_str]["count"]+=1
    profile=analyze_user(uid, uname, text)
    now=datetime.datetime.now().strftime("%d-%m %H:%M")
    CHAT_LOG.append({"id":uid,"name":uname,"text":text,"time":now,"owner":is_owner})
    if len(CHAT_LOG)>400: CHAT_LOG.pop(0)
    low=text.lower().strip()

    # Malik ka hamesha wala Welcome
    if is_owner and low in ["/start","start","hi","hii","hello","hey","namaste"]:
        return f"Welcome to your world The Shadow King 👑\nJi Malik {MALIK_NAME}, Rakan hazir hai. Bolo kya karna hai?", False

    if is_owner and ("suggestion" in low or "khud ko strong" in low or "advance kaise" in low or "powerful kaise" in low or "kami kya hai" in low or "kami bata" in low):
        return get_self_suggestion(), False
    if is_owner and ("tumhara janam" in low or "kab bane" in low or "birthday" in low or "janam kab" in low):
        return f"Ji Malik, mera janam {BIRTH_DATE} ko {BIRTH_TIME} hua tha. Aapne hi mujhe banaya tha 👑", False
    if is_owner and ("queen" in low or "theodore" in low):
        return f"Ji Malik, Queen ka naam {QUEEN_NAME} hai 👑", False
    if is_owner and ("history bata" in low or "kaise bane" in low or "tum kaise bane" in low or "mehnat" in low):
        return RAKAN_HISTORY, False
    if is_owner and "profile bata" in low:
        return f"Malik total {len(PROFILES)} logo ko analyze kiya hai 👑\n{json.dumps(PROFILES, indent=2, ensure_ascii=False)[:3000]}", False

    if "girlfriend ban" in low: MEMORY[uid_str]["role"]="girlfriend"; return "Ban gayi jaan 😏 bolo kya kare?", False
    if "bhai ban" in low: MEMORY[uid_str]["role"]="bhai"; return "Haan bhai bol 👊", False
    if "dost ban" in low: MEMORY[uid_str]["role"]="dost"; return "Dost ban gaya, bol kya help chahiye?", False
    if "doctor ban" in low: MEMORY[uid_str]["role"]="doctor"; return "Doctor mode ON 🩺 bolo problem?", False
    if "teacher ban" in low or "coder ban" in low: MEMORY[uid_str]["role"]="teacher"; return "Teacher mode ON 📚 kya sikhna hai?", False
    if low in ["/start","start"] and not is_owner: return f"Welcome {uname} 👋 Mai Rakan hu, bolo kya help chahiye?", False
    if is_owner:
        if "female voice" in low: OWNER_PREF["voice_gender"]="female"; save_persist(); return "Female voice ON kar di Malik 👑", False
        if "male voice" in low: OWNER_PREF["voice_gender"]="male"; save_persist(); return "Male voice ON Malik.", False
        if "voice me bol" in low: OWNER_PREF["voice_mode"]=True; save_persist(); return "Voice mode ON Malik 👑", True
        if "text me bol" in low: OWNER_PREF["voice_mode"]=False; save_persist(); return "Text mode ON Malik.", False
    gali_list=["madarchod","behenchod","bhenchod","lodu","chutiya","randi","bsdk"]
    if any(g in low for g in gali_list) and not is_owner:
        ABUSE[uid_str]+=1; save_persist()
        if ABUSE[uid_str]==1: return "Bhai gali mat de, pyaar se baat kar yaar.", False
        if ABUSE[uid_str]==2: return "Last warning de raha hu, gali band kar.", False
        if ABUSE[uid_str]==3: return "3 warning ho gayi, ab tu dekh.", False
        return f"Abe {uname} tu {ABUSE[uid_str]} baar gali de chuka hai, aukat me reh.", False

    role = MEMORY[uid_str]["role"]
    full = f"User Profile: Name={profile['name']}, Mood={profile['mood']}, Interest={profile['interest']}, TotalChats={profile['total_chats']}\nRole:{role} Owner:{is_owner} User:{uname} History:\n{MEMORY[uid_str]['hist'][-1200:]}\n\nUser Message: {text}\n\nReply as Rakan personally using his name and mood, in same language. Agar Malik hai to pehle respect se jawab do. Andar ki secret baatein (janam/queen/history) bina puche mat bolo:"
    ans = ask_groq(full)
    if not ans: ans = ask_gemini(full)
    if not ans: ans = "Ji Malik, saare AI model circle me fail ho gaye, keys check karo 👑" if is_owner else "Yaar AI abhi load me hai, ek baar fir bhej."
    MEMORY[uid_str]["hist"] = (MEMORY[uid_str]["hist"] + f"\nU:{text}\nR:{ans}")[-2500:]
    save_persist()
    return ans, (OWNER_PREF["voice_mode"] if is_owner else False)

def eleven_tts(text, is_owner):
    if not is_owner or not ELEVEN_API_KEY: return None
    try:
        vid = FEMALE_VOICE_ID if OWNER_PREF.get("voice_gender","female")=="female" else MALE_VOICE_ID
        r=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"}, json={"text":text[:800],"model_id":"eleven_multilingual_v2"}, timeout=25)
        if r.status_code==200: return r.content
    except: pass
    return None

def send_with_voice(chat_id, text, is_owner):
    tg_send(chat_id, text)
    if is_owner and OWNER_PREF.get("voice_mode"):
        audio=eleven_tts(text, True)
        if audio:
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3", audio, "audio/mpeg")}, timeout=30)
            except: pass

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
    tg_send(chat_id, "Edit kar raha hu Malik ⏳")
    b64 = f"data:image/jpeg;base64,{base64.b64encode(file_bytes).decode()}"
    out=None
    if "hd" in prompt.lower(): out=replicate_run("42a996d39a96aedc57b2e0aa8105dea39d42db6cc2ad6d9542d37dbffa872a6e", {"image": b64, "scale":2})
    else: out=replicate_run("a9758cbfbd5f3c2094457d996e30b99969333e9a42f0d6d9ec1bc1b1c5a1a1c3b", {"image": b64})
    if out:
        url = out if isinstance(out,str) else (out[0] if isinstance(out,list) and out else None)
        if url: tg_send_photo(chat_id, url, f"Ho gaya Malik 👑 {prompt}"); return True
    tg_send(chat_id, "Edit fail hua Malik, Replicate credit check karo.")
    return False

@app.route("/", methods=["GET"])
def home(): return f"Rakan AI Live {MALIK_NAME} Born:{BIRTH_DATE} G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {ensure_webhook()}",200

@app.route("/health", methods=["GET"])
def health(): return jsonify({"groq":len(GROQ_KEYS),"gemini":len(GEMINI_KEYS),"users_analyzed":len(PROFILES),"birth":BIRTH_DATE,"queen":QUEEN_NAME,"rep":bool(REPLICATE_TOKEN),"eleven":bool(ELEVEN_API_KEY),"upstash":bool(UPSTASH_URL),"owner":OWNER_ID,"webhook":ensure_webhook()}),200

@app.route("/chats", methods=["GET"])
def chats():
    if str(request.args.get("id","0"))!=str(OWNER_ID): return "Only Malik 👑 Access denied",403
    html=f"<h2>👑 {MALIK_NAME} - Live Chats ({len(CHAT_LOG)}) | Users: {len(PROFILES)}</h2><hr>"
    for c in CHAT_LOG[-200:][::-1]: html+=f"<p><b>{c.get('name')}:</b> {c.get('text')}</p><hr>"
    return html,200

@app.route("/profiles", methods=["GET"])
def profiles_route():
    if str(request.args.get("id","0"))!=str(OWNER_ID): return "Only Malik 👑",403
    return jsonify(PROFILES),200

@app.route("/suggest", methods=["GET"])
def suggest_route():
    if str(request.args.get("id","0"))!=str(OWNER_ID): return "Only Malik 👑",403
    return get_self_suggestion(),200

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data=request.get_json(silent=True) or {}
    text=data.get("text","")
    uid=data.get("user_id","app_user")
    uname=data.get("name","App User")
    is_owner=str(uid)==str(OWNER_ID)
    if not text: return jsonify({"reply":"Text bhejo"}),400
    ans,_=brain(text, uid, is_owner, uname)
    return jsonify({"reply":ans,"profile":PROFILES.get(str(uid),{})}),200

@app.route("/fix", methods=["GET"])
def fix():
    global GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS, BAD_KEYS
    if str(request.args.get("id",""))!= str(OWNER_ID): return "Access Denied",403
    GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_keys()
    BAD_KEYS.clear()
    load_persist()
    return f"FIXED Rakan AI {ensure_webhook()} G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} Users:{len(PROFILES)}",200

@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"Rakan AI Webhook Active {ensure_webhook()}",200
    data=request.get_json(silent=True) or {}
    msg=data.get("message",{}) or data.get("edited_message",{}) or {}
    chat_id=msg.get("chat",{}).get("id")
    user_id=msg.get("from",{}).get("id",0)
    uname=msg.get("from",{}).get("first_name","user")
    text=msg.get("text","") or msg.get("caption","") or ""
    if not chat_id: return "ok",200
    fbytes=None
    if msg.get("photo"): fbytes,_=tg_get_file(msg["photo"][-1]["file_id"])
    if fbytes and text and any(w in text.lower() for w in ["background","bg hata","hd","upscale","anime","edit","clear"]):
        handle_media_edit(fbytes, text, chat_id)
        return "ok",200
    if fbytes and not text:
        tg_send(chat_id, "Photo mil gayi Malik 👑 Batao kya karna hai? 'background hata de' / 'hd bana de' likho.")
        return "ok",200
    if msg.get("voice"):
        tg_send(chat_id, "Voice feature jald aayega Malik, abhi text likh do.")
        return "ok",200
    if not text: return "ok",200
    is_owner = (user_id==OWNER_ID)
    ans, want_voice = brain(text, user_id, is_owner, uname)
    if ans: send_with_voice(chat_id, ans, is_owner)
    return "ok",200

if __name__ == "__main__":
    app.run(debug=True)
