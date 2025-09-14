import discord
from discord.ext import commands
from discord import app_commands
import os
import json

CONFIG_FILE = "guild_config.json"
WARN_FILE = "warnings.json"

# --- 設定ファイル読み込み ---
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

# --- 設定ファイル保存 ---
def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

guild_config = load_json(CONFIG_FILE)
warnings = load_json(WARN_FILE)

# --- Bot 初期化 ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# --- 言語メッセージ定義 ---
LANGS = {
    "ja": {
        "ngword": "⚠️ {user} 禁止ワードが含まれています！（警告 {count}/3）",
        "invite": "🚫 招待リンクは禁止されています！（警告 {count}/3）",
        "mention": "⚠️ {user} メンションスパムは禁止です！（警告 {count}/3）",
        "spam": "⛔ {user} がスパム行為を行いました！（警告 {count}/3）",
        "warn": "⚠️ {user} に警告を与えました！（理由: {reason}） 警告数: {count}",
        "ban": "⛔ {user} をBANしました（警告3回）"
    },
    "tr": {
        "ngword": "⚠️ {user} yasaklı kelime kullandı! (Uyarı {count}/3)",
        "invite": "🚫 Davet linkleri yasaktır! (Uyarı {count}/3)",
        "mention": "⚠️ {user} aşırı etiketleme yaptı! (Uyarı {count}/3)",
        "spam": "⛔ {user} spam yaptı! (Uyarı {count}/3)",
        "warn": "⚠️ {user} uyarıldı! (Sebep: {reason}) Uyarı sayısı: {count}",
        "ban": "⛔ {user} 3 uyarı aldığı için sunucudan yasaklandı."
    }
}

def get_lang(guild_id: int):
    gid = str(guild_id)
    return guild_config.get(gid, {}).get("lang", "ja")


# --- 警告処理 ---
async def give_warning(member: discord.Member, reason: str, lang: str):
    gid = str(member.guild.id)
    uid = str(member.id)

    if gid not in warnings:
        warnings[gid] = {}
    warnings[gid][uid] = warnings[gid].get(uid, 0) + 1
    count = warnings[gid][uid]
    save_json(WARN_FILE, warnings)

    # BAN判定
    if count >= 3:
        try:
            await member.ban(reason="警告3回")
            return LANGS[lang]["ban"].format(user=member.mention)
        except discord.Forbidden:
            return "❌ BANできません（権限不足）"
    else:
        return LANGS[lang][reason].format(user=member.mention, count=count)


# --- NGワードリスト ---
NG_WORDS = ["küfür", "spam", "amk", "anan", "荒らし", "死ね"]


# --- メッセージ監視イベント ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    lang = get_lang(message.guild.id)

    # NGワード
    for word in NG_WORDS:
        if word in message.content.lower():
            await message.delete()
            msg = await give_warning(message.author, "ngword", lang)
            await message.channel.send(msg, delete_after=5)
            return

    # 招待リンク
    if "discord.gg/" in message.content:
        await message.delete()
        msg = await give_warning(message.author, "invite", lang)
        await message.channel.send(msg, delete_after=5)
        return

    # 大量メンション
    if len(message.mentions) >= 5 or message.mention_everyone:
        await message.delete()
        msg = await give_warning(message.author, "mention", lang)
        await message.channel.send(msg, delete_after=5)
        return

    # スパム検知（5秒間に5メッセージ以上）
    now = discord.utils.utcnow().timestamp()
    uid = message.author.id
    if not hasattr(bot, "msg_log"):
        bot.msg_log = {}
    if uid not in bot.msg_log:
        bot.msg_log[uid] = []
    bot.msg_log[uid] = [t for t in bot.msg_log[uid] if now - t < 5]
    bot.msg_log[uid].append(now)

    if len(bot.msg_log[uid]) > 5:
        msg = await give_warning(message.author, "spam", lang)
        await message.channel.send(msg, delete_after=5)
        return

    await bot.process_commands(message)


# --- スラッシュコマンド: 言語設定 ---
@bot.tree.command(name="setlang", description="サーバーの言語を設定します（ja / tr）")
@app_commands.checks.has_permissions(administrator=True)
async def setlang(interaction: discord.Interaction, lang: str):
    if lang not in LANGS:
        return await interaction.response.send_message("❌ 言語は `ja` または `tr` を指定してください。", ephemeral=True)

    gid = str(interaction.guild.id)
    if gid not in guild_config:
        guild_config[gid] = {}
    guild_config[gid]["lang"] = lang
    save_json(CONFIG_FILE, guild_config)

    await interaction.response.send_message(f"✅ サーバーの言語を `{lang}` に設定しました！", ephemeral=True)


# --- スラッシュコマンド: 警告付与（手動） ---
@bot.tree.command(name="warn", description="ユーザーに警告を与えます（管理者専用）")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "なし"):
    lang = get_lang(interaction.guild.id)
    msg = await give_warning(member, "warn", lang)
    await interaction.response.send_message(msg)


# --- 起動イベント ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ ログイン成功: {bot.user} (ID: {bot.user.id})")


# --- 実行 ---
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOTトークンが環境変数に設定されていません。")

bot.run(TOKEN)
