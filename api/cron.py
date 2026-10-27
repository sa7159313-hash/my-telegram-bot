# api/cron.py - V35.8 FIXED - Weather + Auto Storage Clean
import os, json, requests, datetime
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = str(os.environ.get("OWNER_ID","0")).strip()
OPENWEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN","")
PROJECT_ID = os.environ.get("VERCEL_PROJECT_ID","") or "my-telegram-bot"

def upstash_get(key):
    try:
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=headers, timeout=5)
        if r.status_code==200:
            d=r.json().get("result")
            return json.loads(d) if d else None
    except: pass
    return None

def get_profiles():
    # V35.8 - Naya key pehle, purana fallback
    for k in ["RAKAN_PROFILES_V357","RAKAN_PROFILES_V355","RAKAN_PROFILES_V354","RAKAN_PROFILES"]:
        data = upstash_get(k)
        if data: return data
    return {}

def get_weather_world(city="Varanasi"):
    try:
        city=city.strip().title()
        if OPENWEATHER_KEY:
            r=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric", timeout=6)
            if r.status_code==200:
                d=r.json()
                return f"{d['name']}, {d['sys']['country']}: {d['weather'][0]['description'].title()}, {d['main']['temp']}°C (Feels {d['main']['feels_like']}°C), Humidity {d['main']['humidity']}%, Wind {d['wind']['speed']}m/s"
        r=requests.get(f"https://wttr.in/{city}?format=%C+%t+%h+%w", timeout=6)
        return f"{city}: {r.text}" if r.status_code==200 else f"{city}: Weather N/A"
    except Exception as e:
        return f"{city}: Weather N/A - {e}"

def tg_send(cid, txt):
    try: 
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": txt[:3500]}, timeout=10)
    except: pass

def auto_clean_storage():
    # Agar VERCEL_TOKEN hai to purani deployments auto delete karega
    if not VERCEL_TOKEN or not PROJECT_ID:
        return "skip - no token"
    try:
        url = f"https://api.vercel.com/v6/deployments?projectId={PROJECT_ID}&limit=20"
        h = {"Authorization": f"Bearer {VERCEL_TOKEN}"}
        r = requests.get(url, headers=h, timeout=10).json()
        deps = r.get("deployments",[])
        deleted = 0
        for d in deps[2:]: # latest 2 chhod ke
            created = d.get("created",0)/1000
            age_days = (datetime.datetime.now().timestamp() - created)/86400
            if age_days > 1: # 1 din se purani
                dep_id = d.get("uid")
                requests.delete(f"https://api.vercel.com/v13/deployments/{dep_id}", headers=h, timeout=10)
                deleted+=1
        return f"cleaned {deleted}"
    except Exception as e:
        return f"clean err {e}"

def main_logic():
    try:
        if OWNER_ID=="0" or not BOT_TOKEN: 
            return "no env - BOT_TOKEN/OWNER_ID missing"
        
        profiles = get_profiles()
        # city ya weather_city dono check karega
        owner_data = profiles.get(OWNER_ID, {}) or profiles.get(str(OWNER_ID), {})
        owner_city = owner_data.get("city") or owner_data.get("weather_city") or owner_data.get("city_name") or "Varanasi"
        
        w = get_weather_world(owner_city)
        ist = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%d %b %I:%M %p IST")
        clean_info = auto_clean_storage()
        msg = f"📰 Auto Weather V35.8 {ist}\n📍 {w}\n✅ Your locked city: {owner_city}\n🧹 Storage Clean: {clean_info}\nBot Live"
        tg_send(OWNER_ID, msg)
        return f"sent {owner_city} - {w} - {clean_info}"
    except Exception as e:
        return f"err {e}"

@app.route('/', methods=['GET'])
@app.route('/api/cron', methods=['GET'])
def cron_route():
    result = main_logic()
    return result, 200

@app.route('/<path:path>', methods=['GET'])
def catch_all(path):
    result = main_logic()
    return result, 200

def handler(request):
    result = main_logic()
    return {"statusCode":200,"body": result}
