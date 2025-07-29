from flask import Flask, redirect, request, jsonify
import requests, json, os
from dotenv import load_dotenv
from datetime import datetime
import discord
from discord.ext import commands
from user_agents import parse

load_dotenv()

app = Flask(__name__)
bot_token = os.getenv("DISCORD_BOT_TOKEN")
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
client_id = os.getenv("DISCORD_CLIENT_ID")
client_secret = os.getenv("DISCORD_CLIENT_SECRET")
redirect_uri = os.getenv("DISCORD_REDIRECT_URI")
access_log_file = "access_log.json"

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@app.route("/")
def index():
    return redirect(f"https://discord.com/api/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=identify")

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Code not provided", 400

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "scope": "identify"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    r.raise_for_status()
    access_token = r.json().get("access_token")

    user_headers = {"Authorization": f"Bearer {access_token}"}
    user_info = requests.get("https://discord.com/api/users/@me", headers=user_headers).json()

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = parse(request.headers.get("User-Agent"))
    geo = requests.get(f"https://ipapi.co/{ip}/json/").json()

    info = {
        "username": f"{user_info.get('username')}#{user_info.get('discriminator')}",
        "id": user_info.get("id"),
        "ip": ip,
        "location": f"{geo.get('country_name')} / {geo.get('region')} / {geo.get('city')}",
        "org": geo.get("org"),
        "user_agent": f"{ua.browser.family} {ua.browser.version_string} / {ua.os.family} {ua.os.version_string}",
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        requests.post(webhook_url, json={
            "embeds": [{
                "title": "新しい認証ログ",
                "color": 0x00ffff,
                "fields": [
                    {"name": "ユーザー", "value": info["username"], "inline": True},
                    {"name": "ID", "value": info["id"], "inline": True},
                    {"name": "IP", "value": info["ip"], "inline": True},
                    {"name": "場所", "value": info["location"], "inline": False},
                    {"name": "組織", "value": info["org"], "inline": False},
                    {"name": "UA", "value": info["user_agent"], "inline": False}
                ],
                "footer": {"text": info["timestamp"]}
            }]
        })
    except Exception as e:
        print("Webhook送信エラー:", e)

    try:
        with open(access_log_file, "a") as f:
            json.dump(info, f, ensure_ascii=False)
            f.write(",\n")
    except Exception as e:
        print("ログ保存エラー:", e)

    return jsonify({"message": "認証完了", "user": info})

if __name__ == "__main__":
    app.run(debug=True)