# api/cron.py - V41 FINAL - Storage Clean + Weather Fixed
import os, json, requests, datetime
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = str(os.environ.get("OWNER_ID","0")).strip()
OPENWEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN","")
PROJECT_ID = os.environ.get("VERCEL_PROJECT_ID","") or os.environ.get("VERCEL_PROJECT_ID_CUSTOM","")

def upstash_get(key):
    try:
        if not UPSTASH_URL or not UPSTASH_TOKEN: return None
        h={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=h, timeout=5)
        if r.status_code==200:
            d=r.json().get("result")
            return json.loads(d) if d else None
    except: pass
    return None

def get_weather_world(city="Varanasi"):
    try:
        city=city.strip().title()
        if OPENWEATHER_KEY:
            r=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric", timeout=6)
            if r.status_code==200:
                d=r.json()
                return f"{d['name']}: {d['weather'][0]['description'].title()}, {d['main']['temp']}°C, Humidity {d['main']['humidity']}%"
        r=requests.get(f"https://wttr.in/{city}?format=%C+%t", timeout=6)
        return f"{city}: {r.text}" if r.status_code==200 else f"{city}: N/A"
    except Exception as e:
        return f"{city}: N/A"

def tg_send(cid, txt):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": txt[:3500]}, timeout=10)
    except: pass

def auto_clean_storage():
    if not VERCEL_TOKEN or not PROJECT_ID:
        return "skip - set VERCEL_TOKEN + PROJECT_ID in env"
    try:
        h = {"Authorization": f"Bearer {VERCEL_TOKEN}"}
        real_id = PROJECT_ID
        # Auto convert name to prj_ id
        if not PROJECT_ID.startswith("prj_"):
            pr = requests.get(f"https://api.vercel.com/v9/projects/{PROJECT_ID}", headers=h, timeout=10)
            if pr.status_code==200:
                real_id = pr.json().get("id", PROJECT_ID)
            else:
                return f"project id error {pr.status_code}"
        # Get deployments
        r = requests.get(f"https://api.vercel.com/v6/deployments?projectId={real_id}&limit=40", headers=h, timeout=10)
        if r.status_code!=200:
            return f"api err {r.status_code} {r.text[:60]}"
        deps = r.json().get("deployments",[])
        if len(deps) <= 4:
            return f"skip - only {len(deps)} deps, need >4"
        deleted=0
        for d in deps[4:]: # latest 4 keep
            dep_id=d.get("uid")
            del_r=requests.delete(f"https://api.vercel.com/v13/deployments/{dep_id}", headers=h, timeout=10)
            if del_r.status_code in [200,202,204]:
                deleted+=1
        return f"cleaned {deleted} deps, left {len(deps)-deleted}"
    except Exception as e:
        return f"clean err {str(e)[:100]}"

def main_logic():
    try:
        if OWNER_ID=="0" or not BOT_TOKEN: return "no env"
        profiles = upstash_get("RAKAN_PROFILES_V41") or upstash_get("RAKAN_PROFILES_V357") or {}
        owner_data = profiles.get(OWNER_ID, {})
        owner_city = owner_data.get("city") or "Varanasi"
        w = get_weather_world(owner_city)
        ist = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%d %b %I:%M %p IST")
        clean_info = auto_clean_storage()
        msg = f"📰 Auto V41 {ist}\n📍 {w}\nCity: {owner_city}\n🧹 {clean_info}\nBot Live ✅"
        tg_send(OWNER_ID, msg)
        return msg
    except Exception as e:
        return f"err {e}"

@app.route('/', methods=['GET'])
@app.route('/api/cron', methods=['GET'])
def cron_route():
    return main_logic(), 200

# catch_all hata diya - yehi fault tha
