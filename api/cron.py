# api/cron.py - V35.9 FINAL - Weather + Auto Storage Clean FIXED
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
    if not VERCEL_TOKEN:
        return "skip - no token"
    try:
        h = {"Authorization": f"Bearer {VERCEL_TOKEN}"}
        # 1. Project ka asli prj_ ID nikalo
        real_project_id = PROJECT_ID
        if not PROJECT_ID.startswith("prj_"):
            pr = requests.get(f"https://api.vercel.com/v9/projects/{PROJECT_ID}", headers=h, timeout=10).json()
            real_project_id = pr.get("id", PROJECT_ID)
        
        # 2. Deployments lao
        url = f"https://api.vercel.com/v6/deployments?projectId={real_project_id}&limit=30"
        r = requests.get(url, headers=h, timeout=10).json()
        deps = r.get("deployments",[])
        
        if len(deps) <= 3:
            return f"skip - only {len(deps)} deps"
            
        deleted = 0
        # Latest 3 chhod ke baaki sab delete
        for d in deps[3:]:
            dep_id = d.get("uid")
            del_r = requests.delete(f"https://api.vercel.com/v13/deployments/{dep_id}", headers=h, timeout=10)
            if del_r.status_code in [200,202,204]:
                deleted+=1
                
        return f"cleaned {deleted} | left {len(deps)-deleted}"
    except Exception as e:
        return f"clean err {str(e)[:80]}"

def main_logic():
    try:
        if OWNER_ID=="0" or not BOT_TOKEN: 
            return "no env - BOT_TOKEN/OWNER_ID missing"
        
        profiles = get_profiles()
        owner_data = profiles.get(OWNER_ID, {}) or profiles.get(str(OWNER_ID), {})
        owner_city = owner_data.get("city") or owner_data.get("weather_city") or owner_data.get("city_name") or "Varanasi"
        
        w = get_weather_world(owner_city)
        ist = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%d %b %I:%M %p IST")
        clean_info = auto_clean_storage()
        msg = f"📰 Auto Weather V35.9 {ist}\n📍 {w}\n✅ Your locked city: {owner_city}\n🧹 Storage Clean: {clean_info}\nBot Live"
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
