from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "KING Bot is 100% LIVE! 👑"

@app.route('/<path:path>')
def catch_all(path):
    return "KING Bot is 100% LIVE! 👑"

# Vercel ke liye jaruri hai
if __name__ == "__main__":
    app.run()
