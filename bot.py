import discord
from discord.ext import commands
from discord import app_commands
import json
import os

CONFIG_FILE = "guild_config.json"

# -----------------------
# 設定ファイルの読み書き
# -----------------------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

guild_config = load_config()

# -----------------------
# Discord BOT 設定
# -----------------------
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("BOT_TOKEN")


@bot.event
async def on_ready():
    print(f"{bot.user} が起動しました！")
    try:
        await bot.tree.sync()
        print("✅ スラッシュコマンドを全体に同期しました")
    except Exception as e:
        print(f"同期エラー: {e}")


# -----------------------
# 設定コマンド
# -----------------------

@bot.tree.command(name="set_welcome", description="ウェルカムチャンネルを設定")
async def set_welcome(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = str(interaction.guild.id)
    guild_config[gid] = guild_config.get(gid, {})
    guild_config[gid]["welcome"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ {channel.mention} をウェルカムチャンネルに設定しました！", ephemeral=True)


@bot.tree.command(name="set_bye", description="退出メッセージのチャンネルを設定")
async def set_bye(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = str(interaction.guild.id)
    guild_config[gid] = guild_config.get(gid, {})
    guild_config[gid]["bye"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ {channel.mention} を退出チャンネルに設定しました！", ephemeral=True)


@bot.tree.command(name="set_welcome_message", description="参加メッセージを設定")
async def set_welcome_message(interaction: discord.Interaction, message: str):
    gid = str(interaction.guild.id)
    guild_config[gid] = guild_config.get(gid, {})
    guild_config[gid]["welcome_msg"] = message
    save_config(guild_config)
    await interaction.response.send_message(f"✅ 参加メッセージを設定しました！\n内容: `{message}`", ephemeral=True)


@bot.tree.command(name="set_bye_message", description="退出メッセージを設定")
async def set_bye_message(interaction: discord.Interaction, message: str):
    gid = str(interaction.guild.id)
    guild_config[gid] = guild_config.get(gid, {})
    guild_config[gid]["bye_msg"] = message
    save_config(guild_config)
    await interaction.response.send_message(f"✅ 退出メッセージを設定しました！\n内容: `{message}`", ephemeral=True)


# -----------------------
# イベント
# -----------------------

def format_message(template: str, member: discord.Member) -> str:
    return (
        template.replace("{user}", member.name)
                .replace("{mention}", member.mention)
                .replace("{server}", member.guild.name)
    )

@bot.event
async def on_member_join(member: discord.Member):
    gid = str(member.guild.id)
    data = guild_config.get(gid, {})
    ch_id = data.get("welcome")
    msg = data.get("welcome_msg", "🎉 ようこそ {mention} さん！")

    if ch_id:
        channel = member.guild.get_channel(ch_id)
        if channel:
            await channel.send(format_message(msg, member))


@bot.event
async def on_member_remove(member: discord.Member):
    gid = str(member.guild.id)
    data = guild_config.get(gid, {})
    ch_id = data.get("bye")
    msg = data.get("bye_msg", "👋 {user} さんがサーバーを退出しました。")

    if ch_id:
        channel = member.guild.get_channel(ch_id)
        if channel:
            await channel.send(format_message(msg, member))


# -----------------------
# 起動
# -----------------------
bot.run(TOKEN)
