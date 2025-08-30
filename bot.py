import json
import os
from discord.ext import commands
from discord import app_commands
import discord

CONFIG_FILE = "guild_config.json"

# 設定を保存・読み込みする関数
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 初期化
guild_config = load_config()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ========================
# 設定コマンド
# ========================
@bot.tree.command(name="set_welcome", description="参加通知チャンネルを設定します")
@app_commands.describe(channel="参加通知を送るチャンネル")
async def set_welcome(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = str(interaction.guild.id)
    guild_config.setdefault(gid, {})
    guild_config[gid]["welcome"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ 参加通知チャンネルを {channel.mention} に設定しました。", ephemeral=True)

@bot.tree.command(name="set_bye", description="退出通知チャンネルを設定します")
@app_commands.describe(channel="退出通知を送るチャンネル")
async def set_bye(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = str(interaction.guild.id)
    guild_config.setdefault(gid, {})
    guild_config[gid]["bye"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ 退出通知チャンネルを {channel.mention} に設定しました。", ephemeral=True)

@bot.tree.command(name="set_log", description="ログチャンネルを設定します")
@app_commands.describe(channel="ログを送るチャンネル")
async def set_log(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = str(interaction.guild.id)
    guild_config.setdefault(gid, {})
    guild_config[gid]["log"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ ログチャンネルを {channel.mention} に設定しました。", ephemeral=True)

# ========================
# 設定を使って通知する例
# ========================
@bot.event
async def on_member_join(member: discord.Member):
    gid = str(member.guild.id)
    config = guild_config.get(gid, {})
    ch_id = config.get("welcome")
    if ch_id:
        channel = member.guild.get_channel(ch_id)
        if channel:
            await channel.send(f"🎉 ようこそ {member.mention} さん！")

@bot.event
async def on_member_remove(member: discord.Member):
    gid = str(member.guild.id)
    config = guild_config.get(gid, {})
    ch_id = config.get("bye")
    if ch_id:
        channel = member.guild.get_channel(ch_id)
        if channel:
            await channel.send(f"😢 {member} さんが退出しました。")

async def send_log(guild: discord.Guild, msg: str):
    gid = str(guild.id)
    config = guild_config.get(gid, {})
    ch_id = config.get("log")
    if ch_id:
        channel = guild.get_channel(ch_id)
        if channel:
            await channel.send(f"📝 {msg}")

# ========================
# 起動時
# ========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ ログインしました: {bot.user}")

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
