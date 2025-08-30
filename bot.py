import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import time
from collections import defaultdict
from datetime import timedelta

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
async def set_channel(interaction: discord.Interaction, key: str, channel: discord.TextChannel, name: str):
    gid = str(interaction.guild.id)
    guild_config.setdefault(gid, {})
    guild_config[gid][key] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ {name} を {channel.mention} に設定しました。", ephemeral=True)

@bot.tree.command(name="set_welcome", description="参加通知チャンネルを設定します")
@app_commands.describe(channel="参加通知を送るチャンネル")
async def set_welcome(interaction: discord.Interaction, channel: discord.TextChannel):
    await set_channel(interaction, "welcome", channel, "参加通知チャンネル")

@bot.tree.command(name="set_bye", description="退出通知チャンネルを設定します")
@app_commands.describe(channel="退出通知を送るチャンネル")
async def set_bye(interaction: discord.Interaction, channel: discord.TextChannel):
    await set_channel(interaction, "bye", channel, "退出通知チャンネル")

@bot.tree.command(name="set_log", description="ログチャンネルを設定します")
@app_commands.describe(channel="ログを送るチャンネル")
async def set_log(interaction: discord.Interaction, channel: discord.TextChannel):
    await set_channel(interaction, "log", channel, "ログチャンネル")

# ========================
# イベント
# ========================
@bot.event
async def on_member_remove(member: discord.Member):
    gid = str(member.guild.id)
    ch_id = guild_config.get(gid, {}).get("bye")
    if ch_id:
        by_channel = member.guild.get_channel(ch_id)
        if by_channel:
            embed = discord.Embed(
                title="📡 ユーザーがログアウトしました。",
                description=(
                    f"`{member.display_name}` がサーバーを退出しました。\n\n"
                    f" **表示名**： `{member.display_name}`\n"
                    f"🔗 **ユーザータグ**： `{member.name}#{member.discriminator}`"
                ),
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.set_image(url="https://media.tenor.com/_1HZ7ZDKazUAAAAd/disconnected-signal.gif")
            embed.set_footer(text="📤 Disconnected by black_ルアン")
            await by_channel.send(embed=embed)

async def send_log(guild: discord.Guild, msg: str):
    gid = str(guild.id)
    ch_id = guild_config.get(gid, {}).get("log")
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
