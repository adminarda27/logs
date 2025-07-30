import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from discord import app_commands
import time
from collections import defaultdict
from datetime import timedelta

# --- Discord Bot トークンは環境変数から取得し、なければ直書きトークンを使用 ---
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

WELCOME_CHANNEL_ID = 1380106447458664469
BY_CHANNEL_ID = 1385210506889138196
AUTH_CHANNEL_ID = 1386183004287795341
LOG_CHANNEL_ID = 1
INVITE_TRACK_CHANNEL_ID = 1

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)
tree = bot.tree
invite_cache = {}

# スパム検知用変数
user_message_times = defaultdict(list)
user_offenses = defaultdict(int)
SPAM_THRESHOLD = 5
SPAM_INTERVAL = 5
TIMEOUT_DURATIONS = [600, 1200]  # 秒

# --- Discord Bot イベント ---

@bot.event
async def on_ready():
    print(f"✅ Bot 起動: {bot.user}")
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
        except:
            invite_cache[guild.id] = {}

    for guild in bot.guilds:
        await tree.sync(guild=guild)
    print("🔄 スラッシュコマンド登録完了")

@bot.event
async def on_member_join(member):
    welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel and welcome_channel.permissions_for(member.guild.me).send_messages:
        embed = discord.Embed(
            title="🎮 ようこそ、新たなコミュニティーへ！",
            description=(
                f"{member.mention} がサーバーに参加しました！\n\n"
                f"🧑‍💻 **表示名**： `{member.display_name}`\n"
                f"🔗 **ユーザータグ**： `{member.name}#{member.discriminator}`\n\n"
                f"🔐 認証は <#{AUTH_CHANNEL_ID}> をご利用ください。"
            ),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_image(url="https://i.pinimg.com/originals/a6/f2/ec/a6f2ec0c56158cffd2224f7d2ed51a74.gif")
        embed.set_footer(text="by black_ルアン")
        await welcome_channel.send(embed=embed)

    invite_channel = bot.get_channel(INVITE_TRACK_CHANNEL_ID)
    try:
        invites_before = invite_cache.get(member.guild.id, {})
        invites_after = await member.guild.invites()
        used_invite = next(
            (invite for invite in invites_after if invites_before.get(invite.code, 0) < invite.uses), None
        )
        invite_cache[member.guild.id] = {invite.code: invite.uses for invite in invites_after}
        if invite_channel:
            if used_invite:
                await invite_channel.send(
                    f"📨 {member.mention} は `{used_invite.inviter}` の招待リンク（`{used_invite.code}`）で参加しました。"
                )
            else:
                await invite_channel.send(f"📨 {member.mention} の招待元は特定できませんでした。")
    except Exception as e:
        if invite_channel:
            await invite_channel.send(f"⚠️ 招待追跡失敗: {str(e)}")

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title="🟢 メンバー参加", color=discord.Color.green())
        embed.add_field(name="名前", value=f"{member}", inline=True)
        embed.add_field(name="ユーザーID", value=f"`{member.id}`", inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await log_channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    by_channel = bot.get_channel(BY_CHANNEL_ID)
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

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title="🔴 メンバー退出", color=discord.Color.red())
        embed.add_field(name="名前", value=f"{member}", inline=True)
        embed.add_field(name="ユーザーID", value=f"`{member.id}`", inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await log_channel.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if message.guild is None or (message.author.bot and not message.content):
        return
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
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
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title="✏️ メッセージ編集", color=discord.Color.blue())
        embed.add_field(name="ユーザー", value=f"{before.author} (`{before.author.id}`)", inline=False)
        embed.add_field(name="前", value=before.content[:1024], inline=False)
        embed.add_field(name="後", value=after.content[:1024], inline=False)
        embed.set_footer(text=f"チャンネル: #{before.channel.name}")
        await log_channel.send(embed=embed)

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
            await message.delete()  # スパムを即削除

            if offenses < 2:
                duration = TIMEOUT_DURATIONS[offenses]
                await member.timeout(discord.utils.utcnow() + timedelta(seconds=duration),
                                     reason=f"{offenses+1}回目のスパム検出")
                try:
                    await member.send(
                        f" スパム行為が検出されました（{offenses+1}回目）\n"
                        f"⏱ タイムアウト：{duration//60}分\n"
                        "今後繰り返すとBANされます。"
                    )
                except:
                    pass
                print(f"[SPAM] {member} タイムアウト {duration//60}分")
            else:
                try:
                    await member.send(
                        "🚫 最終警告：スパムが3回検出されたため、あなたはサーバーからBANされました。"
                    )
                except:
                    pass
                await message.guild.ban(member, reason="スパム3回による自動BAN")
                print(f"[SPAM] {member} をBANしました")

        except Exception as e:
            print(f"[スパム処理エラー] {e}")

        user_offenses[member.id] += 1
        user_message_times[member.id] = []

    await bot.process_commands(message)

# --- スラッシュコマンド ---

@tree.command(name="help", description="Botのコマンド一覧を表示します")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📘 Botコマンド一覧", color=discord.Color.blue())
    embed.add_field(name="/ルール", value="スパムルールの説明", inline=False)
    embed.add_field(name="/警告回数", value="自分または指定ユーザーの警告回数を確認", inline=False)
    embed.add_field(name="/認証方法", value="認証方法の案内", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="ルール", description="スパムルールについて説明します")
async def rules_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🚨 スパムルールについて", color=discord.Color.red())
    embed.description = (
        "同じ内容を短時間に複数回送信するとスパムと判定されます。\n"
        f"5回以上連続でメッセージを送ると自動で削除され、{TIMEOUT_DURATIONS[0]//60}分のタイムアウト処置が行われます。\n"
        f"2回目の違反で{TIMEOUT_DURATIONS[1]//60}分のタイムアウト、3回目でBANされます。\n"
        "ルールを守って楽しいコミュニティを作りましょう！"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="警告回数", description="指定ユーザーの警告回数を確認します")
@app_commands.describe(member="警告回数を知りたいユーザーを指定してください（省略時は自身）")
async def offenses_command(interaction: discord.Interaction, member: discord.Member = None):
    if member is None:
        member = interaction.user
    count = user_offenses.get(member.id, 0)
    await interaction.response.send_message(f"{member.mention} の警告回数は {count} 回です。", ephemeral=True)

@tree.command(name="認証方法", description="認証の方法を案内します")
async def auth_method_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🔐 認証方法", color=discord.Color.green())
    embed.description = (
        f"認証は <#{AUTH_CHANNEL_ID}> チャンネルで案内しています。\n"
        "そちらの指示に従って認証を完了してください。\n"
        "問題があれば管理者までお問い合わせください。"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Flaskサーバー起動部分（Koyeb用） ---

app = Flask(__name__)

@app.route("/")
def index():
    return "Discord Bot is running."

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.run(TOKEN)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
