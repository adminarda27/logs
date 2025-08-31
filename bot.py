import discord
from discord.ext import commands
import os
import json

CONFIG_FILE = "guild_config.json"

# --- 設定ファイルのロード/保存 ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

guild_config = load_config()

# --- Discord Intents ---
intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True

# --- Bot本体 ---
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 起動時イベント ---
@bot.event
async def on_ready():
    print(f"✅ ログインしました: {bot.user}")

# --- メンバー参加時 ---
@bot.event
async def on_member_join(member: discord.Member):
    gid = str(member.guild.id)
    ch_id = guild_config.get(gid, {}).get("welcome")
    if ch_id:
        ch = member.guild.get_channel(ch_id)
        if ch:
            embed = discord.Embed(
                title="🎉 新しいメンバーが参加しました！",
                description=f"{member.mention} さん、ようこそ！",
                color=0x00ff00,
            )
            await ch.send(embed=embed)

# --- メンバー退出時 ---
@bot.event
async def on_member_remove(member: discord.Member):
    gid = str(member.guild.id)
    ch_id = guild_config.get(gid, {}).get("bye")
    if ch_id:
        ch = member.guild.get_channel(ch_id)
        if ch:
            embed = discord.Embed(
                title="📡 ユーザーが退出しました。",
                description=f"{member.name} さん、またね！",
                color=0xff0000,
            )
            await ch.send(embed=embed)

# --- コマンド: 設定 ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx, mode: str, channel: discord.TextChannel):
    gid = str(ctx.guild.id)
    if gid not in guild_config:
        guild_config[gid] = {}

    if mode.lower() == "welcome":
        guild_config[gid]["welcome"] = channel.id
        await ctx.send(f"✅ ウェルカムメッセージチャンネルを {channel.mention} に設定しました。")
    elif mode.lower() == "bye":
        guild_config[gid]["bye"] = channel.id
        await ctx.send(f"✅ 退出メッセージチャンネルを {channel.mention} に設定しました。")
    else:
        await ctx.send("❌ モードは `welcome` または `bye` を指定してください。")

    save_config(guild_config)

# --- トークン取得 ---
TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("DISCORD_BOT_TOKEN")
    or os.getenv("DISCORD_TOKEN")
)

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN / DISCORD_BOT_TOKEN / DISCORD_TOKEN が設定されていません。")

bot.run(TOKEN)
