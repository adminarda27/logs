import discord
from discord.ext import commands
from discord import app_commands
import os
import json

CONFIG_FILE = "guild_config.json"

# ===== 設定ファイルの読み書き =====
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

guild_config = load_config()

# ===== Bot 初期化 =====
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = int(os.getenv("GUILD_ID", 0))  # 開発用サーバーに限定して同期可

# ===== 起動時処理 =====
@bot.event
async def on_ready():
    print(f"✅ ログイン成功: {bot.user}")
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            synced = await bot.tree.sync(guild=guild)  # 特定サーバーに同期
            print(f"✅ {len(synced)} 個のスラッシュコマンドを {guild.id} に同期しました")
        else:
            synced = await bot.tree.sync()  # 全サーバーに同期（時間かかる）
            print(f"✅ {len(synced)} 個のスラッシュコマンドをグローバルに同期しました")
    except Exception as e:
        print(f"❌ スラッシュコマンド同期失敗: {e}")

# ====== スラッシュコマンド ======

# 🎉 入退室チャンネル設定
@bot.tree.command(name="set_welcome", description="入室メッセージを送るチャンネルを設定します")
@app_commands.describe(channel="入室メッセージを送るチャンネル")
async def set_welcome(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = str(interaction.guild.id)
    if gid not in guild_config:
        guild_config[gid] = {}
    guild_config[gid]["welcome"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ 入室チャンネルを {channel.mention} に設定しました！", ephemeral=True)

@bot.tree.command(name="set_bye", description="退室メッセージを送るチャンネルを設定します")
@app_commands.describe(channel="退室メッセージを送るチャンネル")
async def set_bye(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = str(interaction.guild.id)
    if gid not in guild_config:
        guild_config[gid] = {}
    guild_config[gid]["bye"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ 退室チャンネルを {channel.mention} に設定しました！", ephemeral=True)

@bot.tree.command(name="set_log", description="ログを送るチャンネルを設定します")
@app_commands.describe(channel="ログを送るチャンネル")
async def set_log(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = str(interaction.guild.id)
    if gid not in guild_config:
        guild_config[gid] = {}
    guild_config[gid]["log"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ ログチャンネルを {channel.mention} に設定しました！", ephemeral=True)

# 🔍 設定確認
@bot.tree.command(name="show_config", description="このサーバーの設定を表示します")
async def show_config(interaction: discord.Interaction):
    gid = str(interaction.guild.id)
    config = guild_config.get(gid, {})
    if not config:
        await interaction.response.send_message("⚠️ このサーバーにはまだ設定がありません。", ephemeral=True)
        return

    welcome = f"<#{config['welcome']}>" if "welcome" in config else "未設定"
    bye = f"<#{config['bye']}>" if "bye" in config else "未設定"
    log = f"<#{config['log']}>" if "log" in config else "未設定"

    embed = discord.Embed(title=f"🛠 サーバー設定 ({interaction.guild.name})", color=0x00BFFF)
    embed.add_field(name="🎉 入室チャンネル", value=welcome, inline=False)
    embed.add_field(name="👋 退室チャンネル", value=bye, inline=False)
    embed.add_field(name="📜 ログチャンネル", value=log, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ====== イベント処理 ======
@bot.event
async def on_member_join(member: discord.Member):
    gid = str(member.guild.id)
    ch_id = guild_config.get(gid, {}).get("welcome")
    if ch_id:
        ch = member.guild.get_channel(ch_id)
        if ch:
            embed = discord.Embed(
                title="🎉 ようこそ！",
                description=f"{member.mention} さんがサーバーに参加しました！",
                color=0x00FF00
            )
            await ch.send(embed=embed)

@bot.event
async def on_member_remove(member: discord.Member):
    gid = str(member.guild.id)
    ch_id = guild_config.get(gid, {}).get("bye")
    if ch_id:
        ch = member.guild.get_channel(ch_id)
        if ch:
            embed = discord.Embed(
                title="👋 さようなら",
                description=f"{member.name} さんがサーバーを退出しました。",
                color=0xFF0000
            )
            await ch.send(embed=embed)

# ====== 実行 ======
if __name__ == "__main__":
    TOKEN = os.getenv("BOT_TOKEN") or os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        raise ValueError("❌ 環境変数に BOT_TOKEN が設定されていません。Render ダッシュボードで追加してください。")
    bot.run(TOKEN)
