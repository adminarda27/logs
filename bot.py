import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from collections import defaultdict
from datetime import timedelta
import time
from dotenv import load_dotenv

# .env ロード（ローカル用）
load_dotenv()

# BOTトークン
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN が設定されていません")

CONFIG_FILE = "guild_config.json"

# 設定の保存・読み込み
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

guild_config = load_config()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)
tree = bot.tree
invite_cache = {}

# スパム関連
user_message_times = defaultdict(list)
user_offenses = defaultdict(int)
SPAM_THRESHOLD = 5
SPAM_INTERVAL = 5
TIMEOUT_DURATIONS = [600, 1200]

# --------------------------
# 起動処理
# --------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot 起動: {bot.user}")
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
        except:
            invite_cache[guild.id] = {}
        await tree.sync(guild=guild)
    print("🔄 スラッシュコマンド登録完了")

# --------------------------
# メンバー参加・退出
# --------------------------
@bot.event
async def on_member_join(member):
    config = guild_config.get(str(member.guild.id), {})
    welcome_channel = bot.get_channel(config.get("welcome_channel"))
    auth_channel_id = config.get("auth_channel")
    invite_channel = bot.get_channel(config.get("invite_track_channel"))
    log_channel = bot.get_channel(config.get("log_channel"))

    # 参加メッセージ
    if welcome_channel and welcome_channel.permissions_for(member.guild.me).send_messages:
        embed = discord.Embed(
            title="🎮 ようこそ！",
            description=f"{member.mention} が参加しました！\n表示名: `{member.display_name}`\nユーザータグ: `{member.name}#{member.discriminator}`\n認証は <#{auth_channel_id}> へ",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await welcome_channel.send(embed=embed)

    # 招待追跡
    try:
        invites_before = invite_cache.get(member.guild.id, {})
        invites_after = await member.guild.invites()
        used_invite = next(
            (invite for invite in invites_after if invites_before.get(invite.code, 0) < invite.uses),
            None
        )
        invite_cache[member.guild.id] = {invite.code: invite.uses for invite in invites_after}
        if invite_channel:
            if used_invite:
                await invite_channel.send(f"📨 {member.mention} は `{used_invite.inviter}` の招待リンクで参加")
            else:
                await invite_channel.send(f"📨 {member.mention} の招待元は特定できませんでした")
    except Exception as e:
        if invite_channel:
            await invite_channel.send(f"⚠️ 招待追跡失敗: {str(e)}")

    # ログ送信
    if log_channel:
        embed = discord.Embed(title="🟢 メンバー参加", color=discord.Color.green())
        embed.add_field(name="名前", value=f"{member}", inline=True)
        embed.add_field(name="ユーザーID", value=f"`{member.id}`", inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await log_channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    config = guild_config.get(str(member.guild.id), {})
    by_channel = bot.get_channel(config.get("bye_channel"))
    log_channel = bot.get_channel(config.get("log_channel"))

    if by_channel:
        embed = discord.Embed(
            title="📡 ユーザー退出",
            description=f"`{member.display_name}` が退出しました\n表示名: `{member.display_name}`\nユーザータグ: `{member.name}#{member.discriminator}`",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await by_channel.send(embed=embed)

    if log_channel:
        embed = discord.Embed(title="🔴 メンバー退出", color=discord.Color.red())
        embed.add_field(name="名前", value=f"{member}", inline=True)
        embed.add_field(name="ユーザーID", value=f"`{member.id}`", inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await log_channel.send(embed=embed)

# --------------------------
# メッセージ編集/削除ログ
# --------------------------
@bot.event
async def on_message_delete(message):
    if message.guild is None or (message.author.bot and not message.content):
        return
    config = guild_config.get(str(message.guild.id), {})
    log_channel = bot.get_channel(config.get("log_channel"))
    if log_channel:
        embed = discord.Embed(title="🗑️ メッセージ削除", color=discord.Color.orange())
        embed.add_field(name="ユーザー", value=f"{message.author} (`{message.author.id}`)", inline=False)
        embed.add_field(name="内容", value=message.content[:1024], inline=False)
        embed.set_footer(text=f"チャンネル: #{message.channel.name}")
        await log_channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
    config = guild_config.get(str(before.guild.id), {})
    log_channel = bot.get_channel(config.get("log_channel"))
    if log_channel:
        embed = discord.Embed(title="✏️ メッセージ編集", color=discord.Color.blue())
        embed.add_field(name="ユーザー", value=f"{before.author} (`{before.author.id}`)", inline=False)
        embed.add_field(name="前", value=before.content[:1024], inline=False)
        embed.add_field(name="後", value=after.content[:1024], inline=False)
        embed.set_footer(text=f"チャンネル: #{before.channel.name}")
        await log_channel.send(embed=embed)

# --------------------------
# スパム検知
# --------------------------
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    now = time.time()
    timestamps = user_message_times[message.author.id]
    timestamps.append(now)
    user_message_times[message.author.id] = [t for t in timestamps if now - t <= SPAM_INTERVAL]

    if len(user_message_times[message.author.id]) >= SPAM_THRESHOLD:
        offenses = user_offenses[message.author.id]
        member = message.author
        try:
            await message.delete()
            if offenses < 2:
                duration = TIMEOUT_DURATIONS[offenses]
                await member.timeout(discord.utils.utcnow() + timedelta(seconds=duration),
                                     reason=f"{offenses+1}回目のスパム検出")
                try:
                    await member.send(f"スパム行為が検出されました（{offenses+1}回目）\n⏱ タイムアウト: {duration//60}分")
                except: pass
            else:
                try: await member.send("🚫 スパム3回で自動BAN")
                except: pass
                await message.guild.ban(member, reason="スパム3回による自動BAN")
        except Exception as e:
            print(f"[スパム処理エラー] {e}")

        user_offenses[member.id] += 1
        user_message_times[member.id] = []

    await bot.process_commands(message)

# --------------------------
# 管理者コマンド: チャンネル設定
# --------------------------
@tree.command(name="設定", description="サーバーのBOTチャンネルを設定")
@app_commands.describe(種類="welcome/bye/auth/log/invite", チャンネル="設定するチャンネル")
async def set_channel(interaction: discord.Interaction, 種類: str, チャンネル: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("管理者権限が必要です", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    if guild_id not in guild_config:
        guild_config[guild_id] = {}
    key_map = {
        "welcome": "welcome_channel",
        "bye": "bye_channel",
        "auth": "auth_channel",
        "log": "log_channel",
        "invite": "invite_track_channel"
    }
    key = key_map.get(種類.lower())
    if not key:
        await interaction.response.send_message("種類は welcome/bye/auth/log/invite から選択してください", ephemeral=True)
        return

    guild_config[guild_id][key] = チャンネル.id
    save_config(guild_config)
    await interaction.response.send_message(f"{種類} チャンネルを {チャンネル.mention} に設定しました", ephemeral=True)

# --------------------------
# スラッシュコマンド: ヘルプ
# --------------------------
@tree.command(name="help", description="Botコマンド一覧")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📘 Botコマンド一覧", color=discord.Color.blue())
    embed.add_field(name="/ルール", value="スパムルールの説明", inline=False)
    embed.add_field(name="/警告回数", value="自分または指定ユーザーの警告回数確認", inline=False)
    embed.add_field(name="/認証方法", value="認証方法の案内", inline=False)
    embed.add_field(name="/設定", value="管理者向け: サーバーでBOTチャンネル設定", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --------------------------
# スラッシュコマンド: ルール・警告・認証
# --------------------------
@tree.command(name="ルール", description="スパムルールについて")
async def rules_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🚨 スパムルール", color=discord.Color.red())
    embed.description = f"{SPAM_THRESHOLD}回以上連続送信で自動削除、1回目{TIMEOUT_DURATIONS[0]//60}分、2回目{TIMEOUT_DURATIONS[1]//60}分、3回目でBAN"
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="警告回数", description="警告回数確認")
@app_commands.describe(member="確認したいユーザー")
async def offenses_command(interaction: discord.Interaction, member: discord.Member = None):
    if member is None:
        member = interaction.user
    count = user_offenses.get(member.id, 0)
    await interaction.response.send_message(f"{member.mention} の警告回数は {count} 回です", ephemeral=True)

@tree.command(name="認証方法", description="認証の案内")
async def auth_method_command(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    auth_channel_id = guild_config.get(guild_id, {}).get("auth_channel")
    embed = discord.Embed(title="🔐 認証方法", color=discord.Color.green())
    if auth_channel_id:
        embed.description = f"認証は <#{auth_channel_id}> で案内しています"
    else:
        embed.description = "管理者が認証チャンネルを設定していません"
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --------------------------
# BOT起動
# --------------------------
bot.run(TOKEN)
