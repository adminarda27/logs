import discord
from discord.ext import commands
import os
import json

CONFIG_FILE = "guild_config.json"

# --- 設定を保存・読み込みする関数 ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

guild_config = load_config()

# --- Discord BOT ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# --- サーバー参加時（ようこそメッセージ） ---
@bot.event
async def on_member_join(member):
    gid = str(member.guild.id)
    ch_id = guild_config.get(gid, {}).get("welcome")
    if ch_id:
        channel = member.guild.get_channel(ch_id)
        if channel:
            embed = discord.Embed(
                title="🎉 ようこそ！",
                description=f"{member.mention} さんがサーバーに参加しました！",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            await channel.send(embed=embed)


# --- サーバー退出時（さよならメッセージ & ログ） ---
@bot.event
async def on_member_remove(member):
    gid = str(member.guild.id)
    ch_id = guild_config.get(gid, {}).get("bye")
    if ch_id:
        by_channel = member.guild.get_channel(ch_id)
        if by_channel:
            embed = discord.Embed(
                title="📡 ユーザーがログアウトしました。",
                description=(
                    f"`{member.display_name}` がサーバーを退出しました。\n\n"
                    f"**表示名**： `{member.display_name}`\n"
                    f"🔗 **ユーザータグ**： `{member.name}#{member.discriminator}`"
                ),
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.set_image(url="https://media.tenor.com/_1HZ7ZDKazUAAAAd/disconnected-signal.gif")
            embed.set_footer(text="📤 Disconnected by black_ルアン")
            await by_channel.send(embed=embed)

    log_id = guild_config.get(gid, {}).get("log")
    if log_id:
        log_channel = member.guild.get_channel(log_id)
        if log_channel:
            embed = discord.Embed(title="🔴 メンバー退出", color=discord.Color.red())
            embed.add_field(name="名前", value=f"{member}", inline=True)
            embed.add_field(name="ユーザーID", value=f"`{member.id}`", inline=True)
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            await log_channel.send(embed=embed)


# --- 設定コマンド（管理者専用） ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx, ctype: str, channel: discord.TextChannel):
    """
    !setchannel welcome #チャンネル
    !setchannel bye #チャンネル
    !setchannel log #チャンネル
    """
    gid = str(ctx.guild.id)
    if gid not in guild_config:
        guild_config[gid] = {}

    if ctype not in ["welcome", "bye", "log"]:
        return await ctx.send("❌ 設定できるのは `welcome` / `bye` / `log` です。")

    guild_config[gid][ctype] = channel.id
    save_config(guild_config)

    await ctx.send(f"✅ {ctype} チャンネルを {channel.mention} に設定しました！")


# --- 起動 ---
@bot.event
async def on_ready():
    print(f"✅ ログイン成功: {bot.user} (ID: {bot.user.id})")
    print("------")

# Render 用 TOKEN
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
bot.run(TOKEN)
