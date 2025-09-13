import discord
from discord.ext import commands
from discord import app_commands
import os
import json

CONFIG_FILE = "guild_config.json"

# --- 設定ファイル読み込み ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# --- 設定ファイル保存 ---
def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

guild_config = load_config()

# --- Bot 初期化 ---
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


# --- 参加時 ---
@bot.event
async def on_member_join(member):
    gid = str(member.guild.id)

    # 自動ロール付与
    role_id = guild_config.get(gid, {}).get("autorole")
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role, reason="自動付与設定")
            except discord.Forbidden:
                print(f"⚠️ {role.name} を {member} に付与できません（権限不足）")

    # ウェルカムメッセージ
    ch_id = guild_config.get(gid, {}).get("welcome")
    if ch_id:
        channel = member.guild.get_channel(ch_id)
        if channel:
            embed = discord.Embed(
                title="🎉 ようこそ！",
                description=f"{member.mention} さんがサーバーに参加しました！",
                color=discord.Color.green()
            )
            avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
            embed.set_thumbnail(url=avatar_url)
            await channel.send(embed=embed)


# --- 退出時 ---
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
            avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
            embed.set_thumbnail(url=avatar_url)
            embed.set_image(url="https://media.tenor.com/_1HZ7ZDKazUAAAAd/disconnected-signal.gif")
            embed.set_footer(text="📤 Disconnected by black_ルアン")
            await by_channel.send(embed=embed)


# --- スラッシュコマンド: チャンネル設定 ---
@bot.tree.command(name="setchannel", description="サーバーのメッセージ送信チャンネルを設定します（管理者専用）")
@app_commands.describe(
    ctype="welcome / bye / log のどれを設定するか",
    channel="設定するテキストチャンネル"
)
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction, ctype: str, channel: discord.TextChannel):
    gid = str(interaction.guild.id)
    if gid not in guild_config:
        guild_config[gid] = {}

    if ctype not in ["welcome", "bye", "log"]:
        return await interaction.response.send_message("❌ 設定できるのは `welcome` / `bye` / `log` です。", ephemeral=True)

    guild_config[gid][ctype] = channel.id
    save_config(guild_config)

    await interaction.response.send_message(
        f"✅ {ctype} チャンネルを {channel.mention} に設定しました！",
        ephemeral=True
    )


# --- スラッシュコマンド: 自動ロール設定 ---
@bot.tree.command(name="setrole", description="自動で付与するロールを設定します（管理者専用）")
@app_commands.describe(
    role="新規参加者に自動で付与するロール"
)
@app_commands.checks.has_permissions(administrator=True)
async def setrole(interaction: discord.Interaction, role: discord.Role):
    gid = str(interaction.guild.id)
    if gid not in guild_config:
        guild_config[gid] = {}

    guild_config[gid]["autorole"] = role.id
    save_config(guild_config)

    await interaction.response.send_message(
        f"✅ 新規参加者に `{role.name}` を自動付与するよう設定しました！",
        ephemeral=True
    )


# --- 起動 ---
@bot.event
async def on_ready():
    await bot.tree.sync()  # スラッシュコマンド同期
    print(f"✅ ログイン成功: {bot.user} (ID: {bot.user.id})")


TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOTトークンが環境変数に設定されていません。")

bot.run(TOKEN)
