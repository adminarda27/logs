import discord
from discord.ext import commands
from discord import app_commands
import time
from collections import defaultdict
from datetime import timedelta
import json
import os
from dotenv import load_dotenv

# -----------------------------
# 環境変数読み込み
# -----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# -----------------------------
# 設定ファイル
# -----------------------------
CONFIG_FILE = "guild_config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

guild_config = load_config()

def get_channel(guild_id, key):
    cid = guild_config.get(str(guild_id), {}).get(key)
    if cid:
        return bot.get_channel(cid)
    return None

# -----------------------------
# Bot本体
# -----------------------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)
tree = bot.tree

# -----------------------------
# 招待リンクキャッシュ
# -----------------------------
invite_cache = {}

# -----------------------------
# スパム検知
# -----------------------------
user_message_times = defaultdict(lambda: defaultdict(list))  # guild_id -> user_id -> [times]
user_offenses = defaultdict(lambda: defaultdict(int))        # guild_id -> user_id -> offenses
SPAM_THRESHOLD = 5
SPAM_INTERVAL = 5
TIMEOUT_DURATIONS = [600, 1200]  # 秒

# -----------------------------
# 起動処理
# -----------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot 起動: {bot.user}")
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
        except:
            invite_cache[guild.id] = {}
    # ギルドごとにスラッシュコマンド同期
    for guild in bot.guilds:
        await tree.sync(guild=guild)
    print("🔄 スラッシュコマンド登録完了")

# -----------------------------
# メンバー参加
# -----------------------------
@bot.event
async def on_member_join(member):
    guild_id = member.guild.id
    welcome_channel = get_channel(guild_id, "welcome")
    if welcome_channel:
        embed = discord.Embed(
            title="🎮 ようこそ、新たなコミュニティーへ！",
            description=(f"{member.mention} がサーバーに参加しました！\n\n"
                         f"🧑‍💻 **表示名**： `{member.display_name}`\n"
                         f"🔗 **ユーザータグ**： `{member.name}#{member.discriminator}`\n\n"
                         f"🔐 認証は <#{get_channel(guild_id, 'auth').id}> をご利用ください。"),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await welcome_channel.send(embed=embed)

    # 招待リンク追跡
    invite_channel = get_channel(guild_id, "invite")
    try:
        invites_before = invite_cache.get(guild_id, {})
        invites_after = await member.guild.invites()
        used_invite = next(
            (invite for invite in invites_after if invites_before.get(invite.code, 0) < invite.uses),
            None
        )
        invite_cache[guild_id] = {invite.code: invite.uses for invite in invites_after}
        if invite_channel:
            if used_invite:
                await invite_channel.send(f"📨 {member.mention} は `{used_invite.inviter}` の招待リンク（`{used_invite.code}`）で参加しました。")
            else:
                await invite_channel.send(f"📨 {member.mention} の招待元は特定できませんでした。")
    except Exception as e:
        if invite_channel:
            await invite_channel.send(f"⚠️ 招待追跡失敗: {str(e)}")

    # ログ
    log_channel = get_channel(guild_id, "log")
    if log_channel:
        embed = discord.Embed(title="🟢 メンバー参加", color=discord.Color.green())
        embed.add_field(name="名前", value=f"{member}", inline=True)
        embed.add_field(name="ユーザーID", value=f"`{member.id}`", inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await log_channel.send(embed=embed)

# -----------------------------
# メンバー退出
# -----------------------------
@bot.event
async def on_member_remove(member):
    guild_id = member.guild.id
    by_channel = get_channel(guild_id, "bye")
    if by_channel:
        embed = discord.Embed(
            title="📡 ユーザーがログアウトしました。",
            description=(f"`{member.display_name}` がサーバーを退出しました。\n\n"
                         f" **表示名**： `{member.display_name}`\n"
                         f"🔗 **ユーザータグ**： `{member.name}#{member.discriminator}`"),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await by_channel.send(embed=embed)

    log_channel = get_channel(guild_id, "log")
    if log_channel:
        embed = discord.Embed(title="🔴 メンバー退出", color=discord.Color.red())
        embed.add_field(name="名前", value=f"{member}", inline=True)
        embed.add_field(name="ユーザーID", value=f"`{member.id}`", inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await log_channel.send(embed=embed)

# -----------------------------
# メッセージ削除・編集ログ
# -----------------------------
@bot.event
async def on_message_delete(message):
    if not message.guild or message.author.bot:
        return
    log_channel = get_channel(message.guild.id, "log")
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
    log_channel = get_channel(before.guild.id, "log")
    if log_channel:
        embed = discord.Embed(title="✏️ メッセージ編集", color=discord.Color.blue())
        embed.add_field(name="ユーザー", value=f"{before.author} (`{before.author.id}`)", inline=False)
        embed.add_field(name="前", value=before.content[:1024], inline=False)
        embed.add_field(name="後", value=after.content[:1024], inline=False)
        embed.set_footer(text=f"チャンネル: #{before.channel.name}")
        await log_channel.send(embed=embed)

# -----------------------------
# スパム検知
# -----------------------------
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    user_id = message.author.id
    now = time.time()
    timestamps = user_message_times[guild_id][user_id]
    timestamps.append(now)
    user_message_times[guild_id][user_id] = [t for t in timestamps if now - t <= SPAM_INTERVAL]

    if len(user_message_times[guild_id][user_id]) >= SPAM_THRESHOLD:
        offenses = user_offenses[guild_id][user_id]
        member = message.author

        try:
            await message.delete()
            if offenses < 2:
                duration = TIMEOUT_DURATIONS[offenses]
                await member.timeout(discord.utils.utcnow() + timedelta(seconds=duration),
                                     reason=f"{offenses+1}回目のスパム検出")
                try:
                    await member.send(f"スパム行為が検出されました（{offenses+1}回目）\n⏱ タイムアウト：{duration//60}分\n今後繰り返すとBANされます。")
                except:
                    pass
            else:
                try:
                    await member.send("🚫 最終警告：スパムが3回検出されたため、あなたはサーバーからBANされました。")
                except:
                    pass
                await message.guild.ban(member, reason="スパム3回による自動BAN")

        except Exception as e:
            print(f"[スパム処理エラー] {e}")

        user_offenses[guild_id][user_id] += 1
        user_message_times[guild_id][user_id] = []

    await bot.process_commands(message)

# -----------------------------
# 設定コマンド（サーバーごと）
# -----------------------------
@tree.command(name="set_welcome", description="ウェルカムチャンネルを設定")
@app_commands.describe(channel="ウェルカムチャンネルを指定")
async def set_welcome(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    guild_config.setdefault(guild_id, {})["welcome"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ ウェルカムチャンネルを {channel.mention} に設定しました。", ephemeral=True)

@tree.command(name="set_bye", description="退出通知チャンネルを設定")
@app_commands.describe(channel="退出通知チャンネルを指定")
async def set_bye(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    guild_config.setdefault(guild_id, {})["bye"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ 退出通知チャンネルを {channel.mention} に設定しました。", ephemeral=True)

@tree.command(name="set_auth", description="認証案内チャンネルを設定")
@app_commands.describe(channel="認証案内チャンネルを指定")
async def set_auth(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    guild_config.setdefault(guild_id, {})["auth"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ 認証案内チャンネルを {channel.mention} に設定しました。", ephemeral=True)

@tree.command(name="set_log", description="ログチャンネルを設定")
@app_commands.describe(channel="ログチャンネルを指定")
async def set_log(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    guild_config.setdefault(guild_id, {})["log"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ ログチャンネルを {channel.mention} に設定しました。", ephemeral=True)

@tree.command(name="set_invite", description="招待追跡チャンネルを設定")
@app_commands.describe(channel="招待追跡チャンネルを指定")
async def set_invite(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    guild_config.setdefault(guild_id, {})["invite"] = channel.id
    save_config(guild_config)
    await interaction.response.send_message(f"✅ 招待追跡チャンネルを {channel.mention} に設定しました。", ephemeral=True)

# -----------------------------
# ヘルプ・ルール・警告回数
# -----------------------------
@tree.command(name="help", description="Botのコマンド一覧")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📘 Botコマンド一覧", color=discord.Color.blue())
    embed.add_field(name="/ルール", value="スパムルールの説明", inline=False)
    embed.add_field(name="/警告回数", value="自分または指定ユーザーの警告回数を確認", inline=False)
    embed.add_field(name="/認証方法", value="認証方法の案内", inline=False)
    embed.set_footer(text="※ メッセージ欄に / を打つと候補が出ます")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="ルール", description="スパムルールの説明")
async def rules_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🚨 スパムルールについて", color=discord.Color.red())
    embed.description = (
        f"同じ内容を短時間に複数回送信するとスパム判定されます。\n"
        f"{SPAM_THRESHOLD}回以上連続で送ると自動削除・タイムアウト処理が行われます。\n"
        f"1回目: {TIMEOUT_DURATIONS[0]//60}分 2回目: {TIMEOUT_DURATIONS[1]//60}分 3回目: BAN\n"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="警告回数", description="警告回数を確認")
@app_commands.describe(member="ユーザーを指定（省略可）")
async def offenses_command(interaction: discord.Interaction, member: discord.Member = None):
    guild_id = interaction.guild.id
    if member is None:
        member = interaction.user
    count = user_offenses[guild_id].get(member.id, 0)
    await interaction.response.send_message(f"{member.mention} の警告回数は {count} 回です。", ephemeral=True)

@tree.command(name="認証方法", description="認証方法の案内")
async def auth_method_command(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    auth_channel = get_channel(guild_id, "auth")
    embed = discord.Embed(title="🔐 認証方法", color=discord.Color.green())
    if auth_channel:
        embed.description = f"認証は <#{auth_channel.id}> チャンネルで案内しています。"
    else:
        embed.description = "認証チャンネルが設定されていません。管理者に問い合わせてください。"
    await interaction.response.send_message(embed=embed, ephemeral=True)

# -----------------------------
# Bot起動
# -----------------------------
bot.run(TOKEN)
